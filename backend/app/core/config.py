"""Central configuration. All tunables live here — no magic numbers scattered in modules."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RIL_", extra="ignore")

    app_name: str = "RIL O2C AI Decision Intelligence Platform"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ril_o2c"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
