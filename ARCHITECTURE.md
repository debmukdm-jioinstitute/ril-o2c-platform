# Architecture

## Layering

```
┌─────────────────────────────────────────────────────────┐
│ frontend/  (Next.js)                                     │
│   fetches JSON from the backend, renders charts/tables    │
└───────────────────────────┬─────────────────────────────┘
                             │ HTTP (JSON)
┌───────────────────────────▼─────────────────────────────┐
│ backend/app/api/*         FastAPI routers                 │
│   - request/response validation via Pydantic schemas      │
│   - no business logic lives here                          │
├───────────────────────────┬─────────────────────────────┤
│ backend/app/services/*    thin glue                       │
│   - market_data.py: selects a data adapter, caches it      │
│   - audit.py: best-effort write to the model-run log       │
├───────────────────────────┬─────────────────────────────┤
│ models/, simulation/,     pure-Python domain logic         │
│ financial/                 (no FastAPI/Pydantic imports —  │
│                             usable from a notebook, a       │
│                             script, or a different API)     │
├───────────────────────────┬─────────────────────────────┤
│ data/adapters/*           swap data sources without         │
│                            touching anything above          │
└───────────────────────────┬─────────────────────────────┘
                             │
                    PostgreSQL (audit trail; optional for
                    forecast/economics — see below)
```

The rule enforced throughout: **`models/`, `simulation/`, and `financial/` never import
anything from `backend/app/api`.** They take plain Python/NumPy/Pandas in, and return plain
dataclasses out — this is what lets `tests/unit/*` exercise the domain logic directly, with no
FastAPI test client and no database. The one deliberate exception is
`app.schemas.governance.ModelGovernance`: every forecaster and the Monte Carlo engine attach one
to their output directly, rather than each domain module inventing its own metadata shape that
`backend/app/schemas/*` would then have to translate. It's treated as a shared, stable,
framework-light contract (a Pydantic model with no FastAPI/routing dependency), not a slide into
importing the API layer's request/response schemas — those (`ForecastRequest`,
`MonteCarloRequest`, etc.) still live only in `backend/app/schemas/*` and stay out of `models/`
and `simulation/` entirely.

## Why the database is optional at request time

Forecast and feedstock-economics endpoints compute everything in-memory from the active data
adapter (synthetic by default) — they do not read from Postgres. Postgres is used only for the
**audit trail** (`ModelRunLog`, `ForecastPoint` in `backend/app/db/models.py`): a durable record
of every model invocation, for traceability (spec module 14). `app/services/audit.py` writes to
it on a best-effort basis — if the database is unreachable, the request still succeeds and a
warning is logged. This was a deliberate choice: a demo/research environment shouldn't go down
because a side-channel audit log couldn't connect.

## Data adapter architecture

`data/adapters/base.py` defines `DataAdapter` with two methods: `load_prices()` and
`load_operational()`. Four implementations exist:

- `SyntheticAdapter` — wraps `data/synthetic/generator.py`, the default.
- `CSVAdapter` / `ExcelAdapter` — read a `date` column plus any subset of the known series
  names from a user-supplied file.
- `APIAdapter` — placeholder; raises `NotImplementedError` until a real provider is wired in.

`backend/app/services/market_data.py` selects an adapter based on `RIL_DATA_SOURCE_MODE` and
caches it for the process lifetime. Nothing downstream (forecasting, feedstock economics, the
API layer) knows or cares which adapter is active — swapping `synthetic` for `csv` is a one-line
config change.

## Forecasting engine internals

`models/forecasting/base.py` defines the `Forecaster` ABC (`fit`, `predict`, `fit_predict`) and
`ForecastResult` (point forecast, 90% interval, governance envelope). Five concrete forecasters
implement it: `NaiveForecaster`, `MovingAverageForecaster`, `ARIMAForecaster` (SARIMAX with a
small AIC-selected order grid), `XGBoostForecaster` and `LightGBMForecaster` (recursive
one-step-ahead with lag/rolling features, quantile-regression intervals), and
`EnsembleForecaster` (weighted average of any of the above, interval widened by cross-model
disagreement). `models/forecasting/gbm_common.py` holds the shared recursive-forecast driver so
XGBoost and LightGBM behave identically except for the underlying booster.

`models/forecasting/backtest.py` implements walk-forward (rolling-window) backtesting and a
strictly chronological train/val/test split — see [METHODOLOGY.md](METHODOLOGY.md) for why this
matters for time series.

LightGBM/XGBoost are optional at import time: if their native extensions fail to load (missing
OpenMP runtime — common on a fresh macOS machine without Homebrew), `models/forecasting/__init__.py`
catches the error, excludes them from `MODEL_REGISTRY` and the default ensemble, and logs a
warning instead of crashing the whole package.

## Feedstock economics internals

`models/feedstock/yields.py` holds illustrative (publicly-documented-order-of-magnitude, not
RIL-specific) steam-cracker yield profiles for ethane/propane/butane/naphtha.
`models/feedstock/economics.py` computes revenue, cost, contribution margin and EBITDA from a
`CrackerEconomicsInputs` dataclass — nothing is hard-coded to favor one feedstock.
`models/feedstock/switch_point.py` builds on top of it: `breakeven_feedstock_price` solves for
the price at which two feedstocks' margins converge (via `scipy.optimize.brentq`), and
`sensitivity_grid_2d`/`sensitivity_surface_3d` sweep a 2D price grid for heatmaps/3D surfaces.

## Monte Carlo scenario engine internals (`simulation/`)

Four modules, each independently testable:

- `market_scenarios.py` — draws a correlated horizon-ahead level for 9 market variables
  (crude/ethane/naphtha/gas/FX/ethylene/propylene/demand/utilisation) via the shared Cholesky
  utility in `data/common/correlation.py`, plus freight (crude-linked + noise) and project
  delay (independent Bernoulli/uniform). `DataFrame` in, `DataFrame` out — no dependency on the
  rest of `simulation/`.
- `economics_mc.py` — a vectorized twin of `models/feedstock/economics.py`'s accounting
  identity, extended with a gas-linked conversion-cost fraction and a freight-augmented
  logistics cost. `tests/unit/test_economics_mc.py` pins it against the scalar engine to catch
  formula drift between the two.
- `financial_mc.py` — per-scenario NPV (fully vectorized) and IRR (`scipy.optimize.brentq`
  per scenario, still fast at 10k+ scenarios since each root-find is a handful of evaluations
  of a closed-form function).
- `distributions.py` — percentile/probability-of-breach/nearest-scenario helpers, used only at
  the end of the pipeline to summarize whatever arrays it's given.

`monte_carlo.py` orchestrates all four into `run_monte_carlo(MonteCarloInputs) ->
MonteCarloResult`, enforces the ≥10,000-scenario floor, and attaches a `ModelGovernance`
envelope exactly like the forecasters do. `MonteCarloResult.raw` keeps every driver's full
scenario array (not just summary stats) — this is what a future reverse-stress-testing module
(spec module 6) would filter and characterize, and what "downside case"/"upside case" in the API
response are built from (the actual scenario nearest the P5/P95 mark, not a reconstructed one).

Only `ethane` and `naphtha` are supported as MC feedstocks in this phase — those are the two
feedstocks with a scenario price variable. The API returns a clear `400` for `propane`/`butane`
pointing at the single-scenario switch-point engine instead.

## Governance envelope

Every forecaster and (where applicable) every economics run attaches a `ModelGovernance` object
(`backend/app/schemas/governance.py`): model name/version, data period, horizon, confidence
level, timestamp, assumptions (plain-English list), data-quality flag
(`synthetic`/`real_unvalidated`/`real_validated`), and the random seed used. The frontend renders
this directly under every chart.

## Frontend

Single Next.js app (`frontend/`), App Router, TypeScript, Tailwind. `lib/api.ts` is a thin
typed fetch client against the backend. `components/ForecastChart.tsx` (Recharts) renders
history + forecast + 90% band; `components/FeedstockTable.tsx` renders the feedstock comparison.
No server-side rendering of API data yet — `app/page.tsx` is a client component that fetches on
mount, which is enough for this phase's control-tower stub.

## Testing strategy

- `tests/unit/*` — domain logic in `models/`, `simulation/`, and `data/`, no HTTP, no DB.
- `tests/integration/test_api.py` — full FastAPI request/response cycle via `TestClient`,
  against the synthetic adapter, without requiring a live Postgres (see above).
- `conftest.py` at the repo root puts both the repo root and `backend/` on `sys.path`, matching
  how `scripts/run_backend.sh` runs the server — so imports behave identically in tests and in
  the running app.
