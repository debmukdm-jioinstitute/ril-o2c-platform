from __future__ import annotations

import lightgbm as lgb
import pandas as pd

from models.forecasting.gbm_common import _GBMForecasterBase


class LightGBMForecaster(_GBMForecasterBase):
    name = "lightgbm"

    def __init__(self, n_estimators: int = 200, max_depth: int = 4, learning_rate: float = 0.05,
                 random_seed: int = 42):
        super().__init__(random_seed)
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate

    def _fit_point(self, X: pd.DataFrame, y: pd.Series):
        model = lgb.LGBMRegressor(
            n_estimators=self.n_estimators, max_depth=self.max_depth,
            learning_rate=self.learning_rate, objective="regression",
            random_state=self.random_seed, verbosity=-1,
        )
        model.fit(X, y)
        return model

    def _fit_quantile(self, X: pd.DataFrame, y: pd.Series, alpha: float):
        model = lgb.LGBMRegressor(
            n_estimators=self.n_estimators, max_depth=self.max_depth,
            learning_rate=self.learning_rate, objective="quantile", alpha=alpha,
            random_state=self.random_seed, verbosity=-1,
        )
        model.fit(X, y)
        return model

    def _predict_row(self, model, row: pd.DataFrame) -> float:
        return float(model.predict(row)[0])
