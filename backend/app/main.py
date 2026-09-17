import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import data, feedstock, financial, forecasting, health, simulation
from app.api.forecasting import warmup_default_forecast
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base, engine
from app.db import models  # noqa: F401  (import so metadata is registered before create_all)
from models.forecasting.warmup import warmup_models

configure_logging()
settings = get_settings()


def _warmup() -> None:
    # Sequenced, not concurrent: on Render's free tier (a single throttled vCPU — confirmed by
    # measuring, not assumed) concurrent CPU-bound work just gets time-sliced on one core with
    # no wall-clock benefit, so there's nothing to gain and some context-switch overhead to lose
    # by running these at the same time. warmup_models() pays each library's one-time init cost
    # on a small dummy series first (cheap, fast); warmup_default_forecast() then runs the
    # actual default UI combo on real data, which both benefits from that already-paid init
    # cost and leaves a genuinely useful cached response behind for the first real visitor.
    warmup_models()
    warmup_default_forecast()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: auto-create tables against the configured Postgres instance.
    # Production deployments should use Alembic migrations instead (see docker/ and docs/).
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # pragma: no cover - degraded mode without a DB
        logging.getLogger(__name__).warning("DB unavailable at startup, audit logging disabled: %s", exc)

    # Fire-and-forget in the background so the server starts accepting requests immediately —
    # see models/forecasting/warmup.py and app/api/forecasting.py's DEFAULT_WARMUP_COMBO for
    # why this exists (one-time library init cost, and a cold forecast cache, that would
    # otherwise land on whichever user's request happens to be first after every cold start —
    # which on Render's free tier is not just "on deploy" but every wake from a 15-min sleep).
    asyncio.create_task(asyncio.to_thread(_warmup))
    yield


app = FastAPI(
    title=settings.app_name,
    description="Probabilistic digital twin for petrochemical economics, market forecasting "
                 "and capacity expansion. Research prototype — synthetic data unless real data "
                 "is explicitly supplied.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Covers local dev (any localhost port) and Vercel deployments by default; override via
    # RIL_CORS_ALLOW_ORIGIN_REGEX for a custom frontend domain.
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(data.router)
app.include_router(forecasting.router)
app.include_router(feedstock.router)
app.include_router(simulation.router)
app.include_router(financial.router)
