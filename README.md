# RIL O2C AI Decision Intelligence Platform

**Probabilistic Digital Twin for Petrochemical Economics, Market Forecasting and Capacity Expansion**

A research prototype demonstrating how AI, probabilistic forecasting, scenario simulation, and
decision intelligence can sit **alongside** an existing linear-programming (LP) feedstock
optimizer — not replace it. This repo does not build an LP solver and does not claim one
feedstock is structurally superior to another; every ranking and every forecast is computed
from the inputs you supply.

All data is **synthetic/demo** unless you explicitly wire in a real source (CSV, Excel, or an
API adapter). Nothing here should be mistaken for actual Reliance Industries data or an actual
market forecast — see [MODEL_CARD.md](MODEL_CARD.md).

## Status

This build covers Phases 1–3 of the roadmap: project skeleton, database, synthetic data,
the market forecasting engine, and the feedstock economics + switch-point engine. See
[RESEARCH_FRAMEWORK.md](RESEARCH_FRAMEWORK.md) for what's built vs. planned.

| Module | Status |
|---|---|
| 1. Market Forecasting Engine | ✅ Built (naive, moving average, ARIMA/SARIMAX, XGBoost, LightGBM, ensemble; backtesting; metrics) |
| 2. Feedstock Economics Engine | ✅ Built |
| 3. Switch-Point Engine | ✅ Built (2D sensitivity grid, 3D surface, break-even solver) |
| 4. Stochastic Scenario Engine (Monte Carlo) | ⏳ Not built — see requirements-optional.txt (PyMC) |
| 5. Capacity Expansion Financial Model | ⏳ Not built |
| 6. Reverse Stress Testing | ⏳ Not built |
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
simulation/  (reserved for Monte Carlo / stochastic scenario engine)
financial/   (reserved for capacity expansion financial model)
data/        Adapters (synthetic/CSV/Excel/API) + synthetic data generator
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

40 tests cover the synthetic generator, every forecaster, backtesting, feedstock economics,
switch-point analysis, and the API layer end-to-end (no live Postgres required — see
`app/services/audit.py`).

### Docker

```bash
docker compose up --build
```

Brings up Postgres, the FastAPI backend (port 8000), and the Next.js frontend (port 3000).

## Design principles this repo follows

- **No fake intelligence.** Every model output carries a governance envelope (model name,
  data period, horizon, confidence interval, timestamp, assumptions, data-quality flag). See
  `app/schemas/governance.py`. Synthetic data is always labeled `"Demo/Synthetic Data"`.
- **Reproducibility.** Every stochastic component takes an explicit random seed; the same
  seed + inputs always produce the same output (see `tests/unit/test_synthetic_generator.py`).
- **No static feedstock ranking.** `models/feedstock/economics.compare_feedstocks` sorts by
  computed contribution margin for whatever prices you give it — see
  `tests/unit/test_feedstock_economics.py::test_compare_feedstocks_ranks_by_margin_no_bias`
  for a test that explicitly flips the ranking by changing prices.
- **Complements, doesn't replace, the existing LP optimizer.** The switch-point engine explains
  *why* a break-even boundary sits where it does; it does not re-solve an allocation problem.
