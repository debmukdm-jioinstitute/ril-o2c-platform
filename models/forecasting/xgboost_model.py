from __future__ import annotations

import pandas as pd
import xgboost as xgb

from models.forecasting.gbm_common import _GBMForecasterBase


class XGBoostForecaster(_GBMForecasterBase):
    name = "xgboost"

    def __init__(self, n_estimators: int = 200, max_depth: int = 4, learning_rate: float = 0.05,
                 random_seed: int = 42):
        super().__init__(random_seed)
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate

    def _fit_point(self, X: pd.DataFrame, y: pd.Series):
        model = xgb.XGBRegressor(
            n_estimators=self.n_estimators, max_depth=self.max_depth,
            learning_rate=self.learning_rate, objective="reg:squarederror",
            random_state=self.random_seed, verbosity=0,
        )
        model.fit(X, y)
        return model

    def _fit_quantile(self, X: pd.DataFrame, y: pd.Series, alpha: float):
        model = xgb.XGBRegressor(
            n_estimators=self.n_estimators, max_depth=self.max_depth,
            learning_rate=self.learning_rate, objective="reg:quantileerror",
            quantile_alpha=alpha, random_state=self.random_seed, verbosity=0,
        )
        model.fit(X, y)
        return model

    def _predict_row(self, model, row: pd.DataFrame) -> float:
        return float(model.predict(row)[0])
