# Model Card

## Scope

This card covers every model currently implemented: the five forecasters in
`models/forecasting/`, their ensemble, the feedstock economics / switch-point engine in
`models/feedstock/`, the Monte Carlo scenario engine in `simulation/`, and the capacity
expansion financial model in `financial/`. It does not cover planned-but-unbuilt modules
(reverse stress testing, performance monitoring, root-cause engine) — see
[METHODOLOGY.md](METHODOLOGY.md) for their intended design.

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

## Monte Carlo scenario engine

**Method:** correlated scenario simulation, not a fitted/trained model — see METHODOLOGY.md §5.
Nine market variables are drawn jointly per scenario via Cholesky factorization of
`DEFAULT_MARKET_CORRELATION` (a hand-specified assumption set, like the daily synthetic
generator's correlation matrix — not estimated from real data). Each scenario is pushed through
the same accounting identity as the feedstock economics engine (vectorized) and a simplified
project-finance layer to produce EBITDA/revenue/margin/NPV/IRR distributions.

**Known limitations:**
- `DEFAULT_MARKET_CORRELATION` is an assumption set, not a fitted/estimated matrix — override it
  via `MonteCarloInputs.correlation` if a calibrated matrix becomes available.
- Only `ethane` and `naphtha` are supported (the only two feedstocks with a scenario price
  variable per the spec's Monte Carlo variable list); `propane`/`butane` are not — see
  `simulation/economics_mc.MC_SUPPORTED_FEEDSTOCKS`.
- NPV/IRR use a **flat EBITDA annuity** (same value every year) and **all-at-once capex** —
  no ramp-up curve, no phased capital deployment. This is a deliberate simplification to keep
  10,000+ scenarios fast to compute; the full capacity expansion financial model (Phase 5, not
  yet built) is where a proper multi-year ramp/phasing belongs.
- Freight and project delay are drawn independently of the correlated market block (see
  METHODOLOGY.md §5 for the reasoning) — if evidence suggests delay risk correlates with market
  conditions (e.g. commissioning delays cluster in high-price environments due to equipment
  competition), that would need to be added explicitly, not assumed away.
- Demand is drawn and reported (and correlated with product prices) but does not independently
  scale sales volume in this build — its economic effect flows through the price correlation
  only.
- IRR is `NaN` for scenarios where no root exists in `[-50%, 500%]` (project never recoups, or
  recoups so richly no realistic discount rate zeroes it) — `DistributionSummary` excludes NaNs
  from its percentiles/mean, so the IRR distribution reported is conditional on IRR being
  well-defined, which is disclosed in the governance assumptions but is worth restating here.

**Evaluation:** `tests/unit/test_monte_carlo.py` and `tests/unit/test_market_scenarios.py`
check reproducibility, percentile ordering, correlation fidelity (empirical correlation of
large-sample draws matches the target matrix within tolerance), and that NPV/IRR respond
correctly to WACC/delay changes. No Monte Carlo output is hard-coded — every number in an API
response is computed live from the request's inputs and seed.

## Capacity expansion financial model

**Method:** deterministic monthly discounted cash flow, not a fitted/trained model — see
METHODOLOGY.md §6. Reuses the exact same accounting identity as the feedstock economics engine
(`compute_cracker_economics`) for every month's EBITDA, scaled by that month's ramp-curve
utilization, so this model and the Phase 3 single-scenario engine cannot silently diverge.

**Known limitations:**
- Pre-tax, unlevered free cash flow — no depreciation, tax shield, or debt/financing schedule.
  A real investment-committee model would need these; this is a decision-support approximation.
- Construction-period capex is spread **evenly** across the months to commissioning — no
  support yet for a real S-curve or milestone-based spend schedule (flagged as a natural
  extension in RESEARCH_FRAMEWORK.md).
- Delay scenarios assume total capex is unchanged by a schedule slip (a pure timing delay);
  if a real delay would also inflate costs (e.g. contractor claims, extended overheads), that
  needs to be modeled as a higher `total_capex_usd` input for that scenario, not assumed away.
- The `accelerated` scenario's benefit is entirely mechanical (earlier cash flows discounted
  less, weighed against `acceleration_cost_usd`) — it does not model execution risk of
  compressing a schedule (e.g. higher probability of rework), which a real capital committee
  would weigh alongside the NPV number.
- IRR is `None`/`null` when no root exists in `[-50%, 500%]`, same reasoning and same bounds as
  the Monte Carlo IRR solver (see MODEL_CARD's Monte Carlo section above).
- `construction_progress_pct` is informational only in this model — it doesn't feed the cash
  flow calculation (only `spent_capex_usd`/`total_capex_usd` do). It exists for the
  `progress_divergence_flag` QA check and for a future executive-dashboard display.

**Evaluation:** `tests/unit/test_project_model.py` and `tests/unit/test_scenarios.py` check that
delay reduces NPV, higher WACC reduces NPV, no EBITDA accrues during construction, the capex
schedule sums exactly to what's expected, steady-state EBITDA matches the scalar economics
engine at full utilization, and that all five standard scenarios are internally consistent
(e.g. longer delay is monotonically worse). No result is hard-coded.

## Fairness / bias note

The one bias risk explicitly guarded against by the spec — assuming a feedstock is structurally
superior — is tested directly: `tests/unit/test_feedstock_economics.py::test_compare_feedstocks_ranks_by_margin_no_bias`
demonstrates the ranking flips when prices are flipped. No other fairness dimensions apply to
this domain (commodity price/economics modeling, not decisions about people).

## Governance

Every forecast, Monte Carlo, and financial-model response carries a `ModelGovernance` envelope:
model name, version, data period, horizon, confidence level, generation timestamp, assumptions,
data-quality flag, random seed (`null` for the financial model, which has no stochastic
component). See `backend/app/schemas/governance.py`.
