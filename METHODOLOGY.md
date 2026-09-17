# Methodology

This document explains the mathematics behind each engine. Sections marked **(planned, not yet
implemented)** describe the intended approach for modules not yet built in this codebase — see
[RESEARCH_FRAMEWORK.md](RESEARCH_FRAMEWORK.md) for build status.

## 1. Synthetic market data

`data/synthetic/generator.py` generates correlated daily series via a mean-reverting
(Ornstein-Uhlenbeck) process in log-price space:

```
d(log P_t) = κ (log P̄ - log P_t) dt + σ dW_t
```

where `P̄` is the long-run anchor level, `κ` ("mean_rev" in `SERIES_SPEC`) is the reversion
speed (half-life = ln(2)/κ), `σ` is annualized volatility, and `dW_t` is a Wiener increment.
Correlation across the nine series is imposed by drawing independent standard-normal shocks and
transforming them through the Cholesky factor of a configurable correlation matrix
(`DEFAULT_CORRELATION`) before feeding them into each series' diffusion term — so, e.g., crude,
naphtha, propane and butane move together (all crude-linked) while ethane/gas move together
(US-gas-linked), matching real commodity market structure at a qualitative level. This is
**not** a calibrated model of actual price history — it exists to produce a plausible,
reproducible, clearly-labeled demo dataset. A fixed `seed` makes generation fully deterministic.

## 2. Forecasting models

All forecasters implement `fit(history) -> predict(horizon) -> ForecastResult` (point forecast +
90% prediction interval). None claim certainty; every interval is nominal 90% and its empirical
coverage is checked during backtesting (`prediction_interval_coverage`).

- **Naive (random walk).** `ŷ_{t+h} = y_t` for all h. Interval standard error grows as
  `σ_r √h` where `σ_r` is the standard deviation of first differences — the textbook result for
  a random walk. This is the floor every other model should beat.
- **Moving average.** `ŷ_{t+h}` = trailing `w`-day mean, held flat. Interval from the residual
  standard deviation of the in-sample MA fit, same `√h` widening.
- **ARIMA/SARIMAX.** `statsmodels.tsa.SARIMAX` fit over a small `(p,d,q)` grid
  `{(1,1,0),(0,1,1),(1,1,1),(2,1,1),(1,1,2)}`, selecting the order with lowest AIC. Interval is
  the model's own 90% confidence interval (`get_forecast(...).conf_int(alpha=0.10)`).
- **XGBoost / LightGBM.** Recursive one-step-ahead forecasting: lag features (1,2,3,5,10,20
  days), rolling mean/std (5/10/20-day windows), and calendar features (day-of-week,
  day-of-month) — see `models/forecasting/features.py`. Point forecast from a
  squared-error-objective model; the 90% interval from two independently-fit quantile-regression
  models (5th and 95th percentile), with quantile crossing corrected by taking
  `min/max` against the point forecast. Because forecasting is recursive, each step's prediction
  feeds the next step's lag features — errors can compound over long horizons, which is stated
  explicitly in the returned governance assumptions.
- **Ensemble.** Weighted average of point forecasts from any subset of the above (default:
  equal weights across all available models). The interval is the weighted average of member
  intervals **widened by the standard deviation of the members' point forecasts** — this avoids
  the common ensemble mistake of averaging away genuine model disagreement into false
  confidence.

### Accuracy metrics (`models/forecasting/metrics.py`)

- **MAE** = mean(|actual − predicted|)
- **RMSE** = sqrt(mean((actual − predicted)²))
- **MAPE** = mean(|actual − predicted| / actual) × 100, undefined (returns `None`, not `inf`)
  when any actual is zero
- **Directional accuracy** = % of periods where sign(Δactual) = sign(Δpredicted)
- **Prediction interval coverage** = % of actuals falling inside the stated interval — compares
  against the nominal 90% to check calibration

### Backtesting (`models/forecasting/backtest.py`)

Two disciplines, both strictly chronological (never randomly shuffled, which would leak future
information into training):

- **Train/val/test split** — a single chronological three-way split by fraction.
- **Rolling-window (walk-forward) backtest** — for each window: fit on all data up to
  `train_end`, forecast `horizon` steps ahead, score against the actuals that follow, then slide
  `train_end` forward by `step` and repeat. Aggregate metrics are computed over the pooled
  actual/predicted arrays across all windows, not averaged window-by-window (so windows with
  more test points aren't under-weighted).

## 3. Feedstock economics (`models/feedstock/economics.py`)

For a given feedstock, throughput, and price scenario:

```
ethylene_tpd  = throughput_tpd × ethylene_yield_pct
propylene_tpd = throughput_tpd × propylene_yield_pct
byproduct_tpd = throughput_tpd × other_byproduct_pct

revenue/day = ethylene_tpd × P_ethylene + propylene_tpd × P_propylene + byproduct_tpd × P_byproduct
feedstock_cost/day = feedstock_price_per_ton_equivalent × throughput_tpd
cash_cost/day = feedstock_cost + conversion_cost + logistics_cost

contribution_margin/day = revenue/day − cash_cost/day
CM per ton ethylene = contribution_margin/day / ethylene_tpd
EBITDA/year = contribution_margin/day × operating_days
```

Ethane and natural gas are priced per MMBtu in the source data; `_feedstock_cost_per_ton_feedstock`
converts using a fixed MMBtu/ton factor (`FeedstockYieldProfile.mmbtu_per_ton`) before the cost
calculation, so all feedstocks are compared on a consistent $/ton-of-feedstock basis. **No
feedstock is given a structural advantage in this formula** — the ranking in
`compare_feedstocks` is purely a sort on the computed `CM per ton ethylene`, which is why
flipping input prices flips the ranking (see the test referenced in the README).

## 4. Switch-point / break-even analysis (`models/feedstock/switch_point.py`)

Given two feedstock scenarios A and B (everything fixed except the price being varied):

- **Break-even price.** Solves `CM_per_ton_ethylene(B, price_b) = CM_per_ton_ethylene(A)` for
  `price_b` using Brent's method (`scipy.optimize.brentq`) — a bracketing root-finder that is
  robust as long as the sign of the gap changes across the supplied bounds (if it doesn't, no
  break-even exists in that range and the function raises rather than returning a nonsense
  answer).
- **2D sensitivity grid.** Evaluates `CM_A(price_a) − CM_B(price_b)` over a Cartesian grid of
  both prices — the sign of this difference tells you which feedstock is preferred at that point
  in the price space; the zero-contour is the break-even boundary.
- **3D surface.** Same computation reshaped into a `Z[i,j]` matrix for a Plotly `Surface` plot.

This engine answers "under what market conditions does A become preferable to B" — it does not
decide how much of each feedstock to actually run; that allocation decision is the existing LP
optimizer's job.

## 5. Stochastic scenario engine / Monte Carlo **(planned, not yet implemented)**

Intended approach: draw ≥10,000 correlated scenarios per run using the same
Cholesky-factorization technique as the synthetic data generator (§1), but applied jointly to
commodity prices, FX, demand, utilization, freight, and project-delay variables in a single
correlated draw per scenario (never independently randomized — see `DEFAULT_CORRELATION` for
the kind of matrix this would reuse/extend). Each scenario would be pushed through the feedstock
economics and financial models to build empirical distributions of EBITDA, revenue, margin, NPV
and IRR, from which percentiles, expected value, and probability-of-threshold-breach are read
off directly (no parametric distribution assumed).

## 6. Capacity expansion financial model **(planned, not yet implemented)**

Intended approach: standard discounted cash flow over the project's construction + operating
life. `NPV = Σ_t FCF_t / (1+r)^t − capex`; `IRR` = the discount rate solving `NPV = 0` (via
`scipy.optimize.brentq` or `numpy_financial.irr`); payback = first period where cumulative FCF
≥ 0. Delay scenarios (1/3/6-month, accelerated) shift the commissioning date and ramp-up curve
and re-run the same DCF — the "economic value/cost" of a scenario is simply the NPV delta
against the base case.

## 7. Reverse stress testing **(planned, not yet implemented)**

Intended approach: given a target (e.g. "EBITDA down 10%"), search the Monte Carlo scenario
population (§5) for the subset that breaches the target, then characterize that subset —
its probability mass (fraction of all scenarios), the marginal distributions of each driver
conditional on membership in the subset (compared to the unconditional distribution — a shift
indicates that driver matters), and a simple driver-importance ranking (e.g. by conditional mean
shift in standard-deviation units). This reuses the Monte Carlo engine rather than requiring a
separate search algorithm.

## 8. Performance monitoring & root-cause decomposition **(planned, not yet implemented)**

Intended approach for the EBITDA variance bridge (predicted vs. actual): a sequential
substitution decomposition — hold all drivers at their predicted values, swap one driver
(feedstock price, product price, FX, utilization, volume, logistics) to its actual value at a
time, and attribute the resulting change in EBITDA to that driver; the residual after all
substitutions is "other" (interaction effects). This is a standard, auditable variance-bridge
technique — an LLM would be used only to narrate the resulting numbers, never to compute them
(spec requirement: the LLM explains, it does not calculate).
