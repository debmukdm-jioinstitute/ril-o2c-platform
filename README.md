# RIL O2C AI Decision Intelligence Platform

**Probabilistic Digital Twin for Petrochemical Economics, Market Forecasting and Capacity Expansion**

A research prototype demonstrating how AI, probabilistic forecasting, scenario simulation, and
decision intelligence can sit **alongside** an existing linear-programming (LP) feedstock
optimizer — not replace it. This repo does not build an LP solver and does not claim one
feedstock is structurally superior to another; every ranking and every forecast is computed
from the inputs you supply.

**Live data.** Crude oil (Brent), natural gas (Henry Hub), propane (Mont Belvieu), and USD/INR
FX are fetched live from the US EIA and the ECB (via frankfurter.dev) — genuine public sources,
free, no fabrication. Ethane, naphtha, butane, ethylene, and propylene have **no free public
spot-price source anywhere** (OPIS/Platts/ICIS-only, thousands of dollars/month) and stay
clearly-labeled synthetic. Nothing here is ever presented as real when it isn't — see
[MODEL_CARD.md](MODEL_CARD.md) and the per-series badges in the UI. Nothing here should be
mistaken for actual Reliance Industries internal data, regardless of source.

## Status

This build covers Phases 1–5 of the roadmap: project skeleton, database, synthetic data,
the market forecasting engine, feedstock economics + switch-point engine, the correlated
Monte Carlo stochastic scenario engine, and the capacity expansion financial model. See
[RESEARCH_FRAMEWORK.md](RESEARCH_FRAMEWORK.md) for what's built vs. planned.

| Module | Status |
|---|---|
| 1. Market Forecasting Engine | ✅ Built (naive, moving average, ARIMA/SARIMAX, XGBoost, LightGBM, ensemble; backtesting; metrics) |
| 2. Feedstock Economics Engine | ✅ Built |
| 3. Switch-Point Engine | ✅ Built (2D sensitivity grid, 3D surface, break-even solver) |
| 4. Stochastic Scenario Engine (Monte Carlo) | ✅ Built (≥10,000 correlated scenarios; EBITDA/revenue/margin/NPV/IRR distributions; probability of threshold breach; downside/upside cases) |
| 5. Capacity Expansion Financial Model | ✅ Built (monthly capex-phasing + ramp-up cash-flow model; NPV/IRR/payback/EBITDA impact; base case + 1/3/6-month delay + accelerated-commissioning scenarios, each priced against base case) |
| 6. Reverse Stress Testing | ⏳ Not built — the Monte Carlo engine already exposes the raw scenario population it would search |
| 7. Performance Monitoring | ⏳ Not built |
| 8. AI Root-Cause Engine | ⏳ Not built |
| 9. AI Copilot | ⏳ Not built |
| 10. Executive Control Tower | ⏳ Not built (a working forecast + feedstock dashboard exists) |
| 11. Research Lab | ⏳ Not built (backtesting API exists; no dedicated UI yet) |

## Architecture

```
frontend/    Next.js + TypeScript + Tailwind — dashboard UI
backend/     FastAPI + Pydantic — API layer, DB models, services
models/      Forecasting and feedstock economics — pure Python, framework-agnostic
simulation/  Monte Carlo scenario engine (correlated draws, vectorized economics, NPV/IRR)
financial/   Capacity expansion financial model (capex phasing, ramp-up, NPV/IRR/payback,
             base/delay/accelerated scenario comparison)
data/        Adapters (synthetic/CSV/Excel/API) + synthetic data generator + shared correlation utility
tests/       Unit + integration tests (pytest)
docs/        Additional documentation
docker/      Dockerfiles; see docker-compose.yml at repo root
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design and [METHODOLOGY.md](METHODOLOGY.md)
for the math behind forecasting, feedstock economics, and switch-point analysis.

## Quickstart

### Backend

```bash
cd backend && python3 -m venv ../.venv && source ../.venv/bin/activate
pip install -r requirements.txt
```

**macOS only:** XGBoost/LightGBM need the OpenMP runtime. If you have Homebrew, run
`brew install libomp`. If not, run `scripts/fix_macos_openmp.sh` from the repo root — it
downloads the equivalent library from conda-forge and patches the installed wheels to find it,
entirely inside `.venv/` (no sudo, no system changes).

```bash
cp .env.example .env   # adjust RIL_DATABASE_URL etc.
./scripts/run_backend.sh   # http://localhost:8000, docs at /docs
```

A Postgres instance is optional for local development — if it's unreachable, the API still
serves forecasts and economics; only the audit-log write is skipped (logged as a warning).
Bring one up with `docker compose up postgres` if you want the audit trail.

**Live market data** (crude/gas/propane/FX) is off by default locally (`RIL_DATA_SOURCE_MODE=synthetic`
in `.env.example`) so the test suite stays deterministic and offline. To run against real data:

```bash
# .env
RIL_DATA_SOURCE_MODE=live
RIL_EIA_API_KEY=DEMO_KEY   # works out of the box at low rate limits; get your own free key
                            # in ~30s at https://www.eia.gov/opendata/register.php for real use
```

Any series a live fetch fails for (rate limit, transient outage) degrades to synthetic
automatically and is labeled as such in every API response and in the UI — see
[data/adapters/live_market.py](data/adapters/live_market.py) and MODEL_CARD.md.

### Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev   # http://localhost:3000
```

### Tests

```bash
PYTHONPATH="$PWD/backend:$PWD" pytest
```

125 tests cover the synthetic generator, every forecaster, backtesting, feedstock economics,
switch-point analysis, the Monte Carlo scenario engine (correlation, vectorized economics,
NPV/IRR, distribution summaries), the capacity expansion financial model (ramp-up, capex
phasing, scenario comparison), the live EIA/FX data clients (mocked network calls — the suite
never depends on network access or live rate limits), and the API layer end-to-end (no live
Postgres required — see `app/services/audit.py`).

### Docker

```bash
docker compose up --build
```

Brings up Postgres, the FastAPI backend (port 8000), and the Next.js frontend (port 3000).

### Free hosted deployment

The code lives at [github.com/debmukdm-jioinstitute/ril-o2c-platform](https://github.com/debmukdm-jioinstitute/ril-o2c-platform).
GitHub itself only serves static files — see [DEPLOYMENT.md](DEPLOYMENT.md) for deploying the
live backend + frontend free on Render + Vercel (both connect straight to this repo).

## Design principles this repo follows

- **No fake intelligence.** Every model output carries a governance envelope (model name,
  data period, horizon, confidence interval, timestamp, assumptions, data-quality flag). See
  `app/schemas/governance.py`. Synthetic data is always labeled `"Demo/Synthetic Data"`; genuine
  live data is labeled `"Live Market Data"` — per series, never a blanket claim. When a live
  fetch fails, the platform degrades to synthetic and says so; it never has an LLM guess a
  number and present it as real (see `data/adapters/live_market.py`).
- **Reproducibility.** Every stochastic component takes an explicit random seed; the same
  seed + inputs always produce the same output (see `tests/unit/test_synthetic_generator.py`).
- **No static feedstock ranking.** `models/feedstock/economics.compare_feedstocks` sorts by
  computed contribution margin for whatever prices you give it — see
  `tests/unit/test_feedstock_economics.py::test_compare_feedstocks_ranks_by_margin_no_bias`
  for a test that explicitly flips the ranking by changing prices.
- **Complements, doesn't replace, the existing LP optimizer.** The switch-point engine explains
  *why* a break-even boundary sits where it does; it does not re-solve an allocation problem.
