import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import data, feedstock, forecasting, health
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base, engine
from app.db import models  # noqa: F401  (import so metadata is registered before create_all)

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: auto-create tables against the configured Postgres instance.
    # Production deployments should use Alembic migrations instead (see docker/ and docs/).
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # pragma: no cover - degraded mode without a DB
        logging.getLogger(__name__).warning("DB unavailable at startup, audit logging disabled: %s", exc)
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
    # Dev frontend can run on any localhost port (3000 by default, 3010+ when that's taken) —
    # this regex covers all of them without opening CORS up to non-localhost origins.
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(data.router)
app.include_router(forecasting.router)
app.include_router(feedstock.router)
