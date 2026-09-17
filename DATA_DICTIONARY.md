# Data Dictionary

## Price series (`data/synthetic/generator.SERIES_SPEC`, adapter `load_prices()`)

| Series name | Unit | Description |
|---|---|---|
| `crude_brent_usd_bbl` | USD/bbl | Brent crude oil |
| `ethane_usd_mmbtu` | USD/MMBtu | Ethane |
| `naphtha_usd_ton` | USD/ton | Naphtha |
| `propane_usd_ton` | USD/ton | Propane |
| `butane_usd_ton` | USD/ton | Butane |
| `natural_gas_usd_mmbtu` | USD/MMBtu | Natural gas |
| `ethylene_usd_ton` | USD/ton | Ethylene |
| `propylene_usd_ton` | USD/ton | Propylene |
| `fx_usdinr` | INR per USD | USD/INR exchange rate |

All series are daily, business-day frequency (`pd.bdate_range`), synthetic by default — see
METHODOLOGY.md §1 for how they're generated and DATA_QUALITY notes below.

## Operational series (adapter `load_operational()`)

| Column | Unit | Description |
|---|---|---|
| `demand_index` | index, 100 = base | Synthetic demand proxy |
| `utilisation_pct` | % | Cracker utilization, bounded [60, 100] |
| `freight_usd_ton` | USD/ton | Freight cost, correlated with crude |
| `project_delay_days` | days | Sparse Poisson-arrival delay events, ≥ 0 |

## Feedstock economics inputs (`CrackerEconomicsInputs`, `backend/app/schemas/feedstock.py`)

| Field | Unit | Notes |
|---|---|---|
| `feedstock` | enum | One of `ethane`, `propane`, `butane`, `naphtha` |
| `feedstock_price` | USD/ton, or USD/MMBtu for ethane | See `FeedstockYieldProfile.price_unit` |
| `throughput_tons_day` | tons/day | Feedstock intake rate |
| `ethylene_price_usd_ton` | USD/ton | Realized ethylene sale price |
| `propylene_price_usd_ton` | USD/ton | Realized propylene sale price |
| `byproduct_price_usd_ton` | USD/ton | Blended realizable value of other co-products |
| `conversion_cost_usd_ton_feedstock` | USD/ton feedstock | Cash opex to crack, ex-feedstock, ex-logistics |
| `logistics_cost_usd_ton_feedstock` | USD/ton feedstock | Transport/handling |
| `fx_usdinr` | INR per USD | Default 83.5 |
| `operating_days` | days/year | Default 330 (accounts for planned/unplanned downtime) |

## Feedstock yield profiles (`models/feedstock/yields.YIELD_PROFILES`)

| Feedstock | Ethylene yield | Propylene yield | Other byproduct | Price basis |
|---|---|---|---|---|
| Ethane | 80% | 2% | 18% | USD/MMBtu (45.5 MMBtu/ton) |
| Propane | 45% | 16% | 39% | USD/ton |
| Butane | 38% | 17% | 45% | USD/ton |
| Naphtha | 31% | 16% | 53% | USD/ton |

Illustrative, publicly-documented order-of-magnitude figures — not RIL-specific plant data.

## Monte Carlo request (`MonteCarloRequest`, `backend/app/schemas/simulation.py`)

| Field | Unit | Notes |
|---|---|---|
| `feedstock` | enum | `ethane` or `naphtha` only — see MODEL_CARD.md for why |
| `throughput_tons_day` | tons/day | Base feedstock intake before utilisation scaling |
| `byproduct_price_usd_ton` | USD/ton | Fixed (not a scenario variable) |
| `conversion_cost_usd_ton_feedstock` | USD/ton | Base conversion cost |
| `conversion_cost_gas_linked_fraction` | 0–1 | Share of conversion cost scaling with the natural-gas price draw; default 0.3 |
| `logistics_cost_usd_ton_feedstock` | USD/ton | Fixed handling component (freight is added on top, drawn per scenario) |
| `operating_days` | days/year | Default 330 |
| `capex_usd` | USD | Project capex, spent at t=0 |
| `project_life_years` | years | Cash-flow annuity length |
| `wacc` | fraction | Annual discount rate, e.g. 0.11 |
| `horizon_years` | years | Decision horizon for the market scenario draw; default 1.0 |
| `n_scenarios` | count | ≥ 10,000 (enforced); default 10,000 |
| `seed` | int | Default 42 |
| `ebitda_threshold_usd_year` | USD | Optional; enables `probability_ebitda_breach` |
| `ebitda_threshold_direction` | `below`\|`above` | Default `below` |

## Monte Carlo scenario variables (`simulation.market_scenarios.MARKET_VARS`)

| Variable | Unit | Correlated? |
|---|---|---|
| `crude` | USD/bbl | ✅ part of the 9-variable correlated block |
| `ethane` | USD/MMBtu | ✅ |
| `naphtha` | USD/ton | ✅ |
| `natural_gas` | USD/MMBtu | ✅ |
| `fx` | INR/USD | ✅ |
| `ethylene` | USD/ton | ✅ |
| `propylene` | USD/ton | ✅ |
| `demand` | index, 100=base | ✅ |
| `utilisation` | % | ✅ |
| `freight` | USD/ton | Deterministic crude-linked component + independent noise (not in the correlated block) |
| `project_delay_days` | days | Independent Bernoulli/uniform draw (execution risk, not market risk) |

## Monte Carlo response (`MonteCarloResponse`)

| Field | Description |
|---|---|
| `revenue`, `ebitda_usd_year`, `margin_pct`, `npv`, `irr` | Each a `DistributionOut`: mean, std, min, max, and percentiles {1,5,10,25,50,75,90,95,99} |
| `probability_ebitda_breach` | Fraction of scenarios breaching `ebitda_threshold_usd_year`, or `null` if no threshold given |
| `downside_case` / `upside_case` | Every driver's value for the actual scenario nearest the P5 / P95 EBITDA mark — an internally consistent scenario, not a reconstructed one |
| `governance` | Same `ModelGovernance` envelope as every forecast |

## Capacity expansion financial model request (`CapexProjectRequest`, `backend/app/schemas/financial.py`)

| Field | Unit | Notes |
|---|---|---|
| `capex.total_capex_usd` | USD | Total project capex |
| `capex.committed_capex_usd` | USD | Contractually committed portion, ≤ total |
| `capex.spent_capex_usd` | USD | Already spent, ≤ committed — sunk, excluded from NPV |
| `capex.construction_progress_pct` | % | Physical progress, independent of cash spend |
| `operating.feedstock` | enum | Any of the four (`ethane`/`propane`/`butane`/`naphtha`) — unlike Monte Carlo, this model reuses the full single-scenario economics engine |
| `operating.nameplate_throughput_tons_day` | tons/day | Full-capacity feedstock intake |
| `operating.*_price*`, `operating.*_cost*` | see DATA_DICTIONARY §"Feedstock economics inputs" | Same fields/units as the Phase 3 economics engine |
| `wacc` | fraction | Annual discount rate |
| `valuation_date` | date | t=0 for discounting |
| `planned_commissioning_date` | date | Base-case commissioning date |
| `ramp_up_months` | months | Length of the default linear ramp; default 6 |
| `ramp_start_utilisation_pct` | % | Ramp starting utilization; default 30 |
| `post_ramp_operating_life_years` | years | Steady-state operating period after ramp completes |
| `delay_days` | days | Applied to `/project` only — `/scenarios` always evaluates a clean zero-delay base case regardless of this field |
| `acceleration_days` / `acceleration_cost_usd` | days / USD | Only used by `/project`, and by `/scenarios`' `accelerated` scenario (which only appears if both are > 0) |

## Capacity expansion financial model response

| Field | Description |
|---|---|
| `npv_usd`, `irr_annual`, `payback_months` | `irr_annual`/`payback_months` are `null` when no root/breakeven exists in range |
| `total_capex_deployed_usd` | `remaining_capex_usd + acceleration_cost_usd` — what's actually discounted (excludes sunk `spent_capex_usd`) |
| `steady_state_annual_ebitda_usd` | Annual EBITDA once the ramp curve reaches its final value |
| `commissioning_date`, `months_to_commission` | Effective (delay/acceleration-adjusted) commissioning date |
| `schedule` | One row per month: `phase` (`construction`\|`ramp_up`\|`steady_state`), `utilisation_pct`, `capex_outflow_usd`, `ebitda_usd`, `fcf_usd`, `cumulative_fcf_usd`, `pv_usd` |
| `governance` | `ModelGovernance`, built once per API response (see ARCHITECTURE.md) |

`ScenarioComparisonResponse` (`/api/financial/scenarios`) wraps a `dict[str, ScenarioSummaryOut]`
keyed by `base_case`, `delay_1_month`, `delay_3_month`, `delay_6_month`, and (conditionally)
`accelerated` — each entry adds `npv_delta_vs_base_usd`, `irr_delta_vs_base_pp`,
`payback_delta_months`, `ebitda_impact_delta_usd` on top of the same summary fields as a single
project result.

## Governance envelope (`ModelGovernance`, every model response)

| Field | Type | Description |
|---|---|---|
| `model_name` | string | e.g. `"ensemble"`, `"xgboost"` |
| `model_version` | string | Semver, currently `"1.0.0"` everywhere |
| `data_period_start` / `data_period_end` | date | Range of history the model was fit on |
| `forecast_horizon_days` | int | Steps requested |
| `confidence_level` | float | 0.90 for all forecasters currently |
| `generated_at` | datetime (UTC) | Response generation time |
| `assumptions` | string[] | Plain-English caveats specific to this run |
| `data_quality` | enum | `synthetic` \| `real_unvalidated` \| `real_validated` |
| `random_seed` | int \| null | Seed used, for reproducibility |

## Database tables (`backend/app/db/models.py`)

| Table | Purpose |
|---|---|
| `market_price_observations` | Optional persisted price history (series_name, obs_date, value, source) |
| `model_run_log` | Audit trail: one row per model invocation (model, module, seed, data quality, inputs/outputs JSON, timestamp) |
| `forecast_points` | Optional persisted forecast output, FK to `model_run_log` |

Only `model_run_log` is currently written to (by `app/services/audit.py`, best-effort — see
ARCHITECTURE.md). The other two tables are defined for future use (e.g. persisting real market
data snapshots) but not yet populated by any code path.
