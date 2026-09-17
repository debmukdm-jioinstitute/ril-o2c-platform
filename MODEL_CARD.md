# Model Card

## Scope

This card covers every model currently implemented: the five forecasters in
`models/forecasting/`, their ensemble, and the feedstock economics / switch-point engine in
`models/feedstock/`. It does not cover planned-but-unbuilt modules (Monte Carlo, financial
model, root-cause engine) — see [METHODOLOGY.md](METHODOLOGY.md) for their intended design.

## Intended use

Research/decision-support prototype for exploring petrochemical market forecasting and
feedstock economics methodology. **Not validated against real market outcomes** — see
Limitations. Not a trading signal, not investment advice, not a substitute for the existing LP
feedstock optimizer.

## Training / fitting data

All models in this build fit against `data/synthetic/generator.py` output by default —
synthetic, seed-reproducible, explicitly labeled `"Demo/Synthetic Data"` throughout the API and
UI (`app/schemas/governance.DataQualityStatus`). Swapping to `CSVAdapter`/`ExcelAdapter` fits
the same models against user-supplied data instead; nothing in the model code changes.

## Forecasting models

| Model | Class | Interval method |
|---|---|---|
| Naive random walk | `NaiveForecaster` | √h-scaled residual std |
| Moving average | `MovingAverageForecaster` | √h-scaled residual std |
| ARIMA/SARIMAX | `ARIMAForecaster` | Native SARIMAX 90% CI |
| XGBoost | `XGBoostForecaster` | 5th/95th percentile quantile regression |
| LightGBM | `LightGBMForecaster` | 5th/95th percentile quantile regression |
| Ensemble | `EnsembleForecaster` | Weighted member intervals + disagreement widening |

**Known limitations:**
- ARIMA order search is a fixed 5-candidate grid, not a full auto-ARIMA search — chosen for
  backtest speed, at the cost of some model flexibility.
- XGBoost/LightGBM forecast recursively (each step's prediction feeds the next step's lag
  features); errors can compound over long horizons. This is disclosed in every forecast's
  `governance.assumptions`.
- Quantile-regression intervals from independently-fit models can cross; the code enforces
  `lower ≤ point ≤ upper` post-hoc rather than jointly optimizing for calibration.
- No model in this build accounts for structural breaks (e.g. a sudden geopolitical shock) —
  all are fit purely on historical statistical patterns.
- LightGBM/XGBoost require a working OpenMP runtime; if unavailable, LightGBM is silently
  excluded from the registry (see ARCHITECTURE.md) rather than crashing forecasting entirely.

**Evaluation:** `models/forecasting/backtest.rolling_backtest` walk-forward backtests any
registered model against any series, reporting MAE/RMSE/MAPE/directional accuracy/interval
coverage per window and pooled. No backtest results are hard-coded anywhere in this repo — they
are computed live against whatever data adapter is active.

## Feedstock economics engine

**Method:** deterministic accounting identity (revenue − cash costs = contribution margin →
EBITDA), not a statistical/ML model — see METHODOLOGY.md §3. Yield profiles
(`models/feedstock/yields.py`) are illustrative, publicly-documented order-of-magnitude figures
for steam-cracker yields by feedstock, **not RIL-specific plant data**. Swap in real yield
curves when available; the economics formulas are unaffected.

**Known limitations:**
- Single-point yields per feedstock (no yield-vs-severity curve, no co-feeding/blending).
- No fixed-cost layer — EBITDA here equals contribution margin at the granularity modeled.
- Byproduct value is a single blended price, not a full product slate.

## Switch-point engine

**Method:** deterministic root-finding (`scipy.optimize.brentq`) and grid evaluation over the
economics engine above — inherits all of its limitations. The break-even solver raises rather
than guessing when no break-even exists in the supplied price bounds (see
`tests/unit/test_switch_point.py::test_breakeven_raises_outside_bounds`).

## Fairness / bias note

The one bias risk explicitly guarded against by the spec — assuming a feedstock is structurally
superior — is tested directly: `tests/unit/test_feedstock_economics.py::test_compare_feedstocks_ranks_by_margin_no_bias`
demonstrates the ranking flips when prices are flipped. No other fairness dimensions apply to
this domain (commodity price/economics modeling, not decisions about people).

## Governance

Every forecast response carries a `ModelGovernance` envelope: model name, version, data period,
horizon, confidence level, generation timestamp, assumptions, data-quality flag, random seed.
See `backend/app/schemas/governance.py`.
