import logging

from models.forecasting.arima_model import ARIMAForecaster
from models.forecasting.base import Forecaster, ForecastResult
from models.forecasting.ensemble import EnsembleForecaster
from models.forecasting.moving_average import MovingAverageForecaster
from models.forecasting.naive import NaiveForecaster
from models.forecasting.xgboost_model import XGBoostForecaster

logger = logging.getLogger(__name__)

# LightGBM's compiled extension needs the system OpenMP runtime (libomp on macOS, via
# Homebrew: `brew install libomp`). When it's missing we degrade gracefully — the rest of the
# platform (and the ensemble) still works with one fewer member — rather than failing to import
# the whole forecasting package over one optional model.
try:
    from models.forecasting.lightgbm_model import LightGBMForecaster
    _LIGHTGBM_AVAILABLE = True
except (ImportError, OSError) as exc:
    LightGBMForecaster = None  # type: ignore[assignment]
    _LIGHTGBM_AVAILABLE = False
    logger.warning("LightGBM unavailable (%s) — excluded from MODEL_REGISTRY and the default ensemble.", exc)

MODEL_REGISTRY = {
    "naive": lambda seed=42: NaiveForecaster(random_seed=seed),
    "moving_average": lambda seed=42: MovingAverageForecaster(random_seed=seed),
    "arima": lambda seed=42: ARIMAForecaster(random_seed=seed),
    "xgboost": lambda seed=42: XGBoostForecaster(random_seed=seed),
}
if _LIGHTGBM_AVAILABLE:
    MODEL_REGISTRY["lightgbm"] = lambda seed=42: LightGBMForecaster(random_seed=seed)


def build_default_ensemble(seed: int = 42) -> EnsembleForecaster:
    members = [
        NaiveForecaster(random_seed=seed),
        MovingAverageForecaster(random_seed=seed),
        ARIMAForecaster(random_seed=seed),
        XGBoostForecaster(random_seed=seed),
    ]
    if _LIGHTGBM_AVAILABLE:
        members.append(LightGBMForecaster(random_seed=seed))
    return EnsembleForecaster(members=members, random_seed=seed)


MODEL_REGISTRY["ensemble"] = build_default_ensemble

__all__ = [
    "Forecaster", "ForecastResult", "NaiveForecaster", "MovingAverageForecaster",
    "ARIMAForecaster", "XGBoostForecaster", "LightGBMForecaster", "EnsembleForecaster",
    "MODEL_REGISTRY", "build_default_ensemble", "_LIGHTGBM_AVAILABLE",
]
