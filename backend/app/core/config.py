"""Central configuration. All tunables live here — no magic numbers scattered in modules."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RIL_", extra="ignore")

    app_name: str = "RIL O2C AI Decision Intelligence Platform"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ril_o2c"

    @field_validator("database_url")
    @classmethod
    def _normalize_postgres_scheme(cls, v: str) -> str:
        # Hosted providers (Render, Heroku-style) commonly hand back a bare "postgres://" or
        # "postgresql://" connection string; SQLAlchemy needs the driver named explicitly for
        # the psycopg3 dialect we install. Normalize rather than requiring every deploy target
        # to know this detail.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix) and "+psycopg" not in v.split("://", 1)[0]:
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    # Reproducibility: every stochastic process in the platform seeds from this.
    random_seed: int = 42

    # Synthetic data is the default data source until real/confidential data is supplied.
    data_source_mode: str = "synthetic"  # synthetic | csv | excel | api

    # Monte Carlo defaults
    mc_default_scenarios: int = 10_000

    # Forecasting defaults
    forecast_default_horizon_days: int = 90
    backtest_min_train_days: int = 365

    log_level: str = "INFO"

    # Regex of allowed CORS origins. Covers local dev (any localhost port) and Vercel preview/
    # production deployments (*.vercel.app) by default; override for a custom frontend domain.
    cors_allow_origin_regex: str = r"http://localhost:\d+|https://.*\.vercel\.app"


@lru_cache
def get_settings() -> Settings:
    return Settings()
