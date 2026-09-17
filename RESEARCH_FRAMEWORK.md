# Research Framework

## Purpose

This platform exists to demonstrate a methodology, not to ship a finished product. Every module
should be judged on: (1) is the math right, (2) is uncertainty represented honestly, (3) can the
result be reproduced, (4) does it complement rather than duplicate the company's existing LP
optimizer.

## Build order and status

Phases follow the original spec's numbering. This build (this session) completed Phases 1–3.

| Phase | Scope | Status |
|---|---|---|
| 1 | Architecture, database, synthetic data | ✅ Done |
| 2 | Forecasting engine | ✅ Done |
| 3 | Feedstock economics + switch-point engine | ✅ Done |
| 4 | Monte Carlo / stochastic scenario engine | Not started |
| 5 | Capacity expansion financial model | Not started |
| 6 | Reverse stress testing | Not started |
| 7 | AI Copilot | Not started |
| 8 | Executive dashboard | Partial — a working forecast + feedstock control-tower view exists (`frontend/app/page.tsx`); not the full spec'd Executive Control Tower (no NPV/IRR/scenario-risk/model-confidence rollup yet, since those modules aren't built) |
| 9 | Research Lab | Partial — backtesting is fully implemented and API-accessible; no dedicated Research Lab UI (model comparison, parameter tuning, export) yet |
| 10 | Testing + documentation + deployment | Partial — 40 passing tests for everything built so far, full doc set, Docker Compose for local deployment; no CI pipeline configured yet |

## What "done" means for a phase in this repo

- Real computation, not mocked/hard-coded outputs (spec module 16: no fake intelligence).
- Unit tests that would fail if the logic were wrong (not just "does it run").
- A governance envelope on every model output (spec module 15).
- Synthetic data clearly labeled as such everywhere it surfaces (API responses, UI).
- Documented in METHODOLOGY.md with the actual formulas/algorithms used.

## Known gaps to close in the next phase (Monte Carlo, Phase 4)

- `backend/requirements-optional.txt` lists `pymc`/`arviz` — not installed by default since
  nothing uses them yet.
- `simulation/` exists as an empty package (`__init__.py` only) — this is where the correlated
  Monte Carlo engine belongs, reusing `DEFAULT_CORRELATION`'s Cholesky-factorization approach
  from `data/synthetic/generator.py` (see METHODOLOGY.md §5 for the intended design) and feeding
  scenario draws through `models/feedstock/economics.py`.
- `financial/` exists as an empty package — this is where the capacity expansion DCF model
  belongs (METHODOLOGY.md §6).

## Reproducibility contract

Every function that involves randomness takes an explicit `seed` (or `random_seed` on a class)
and defaults to `42`. `tests/unit/test_synthetic_generator.py::test_deterministic_given_seed`
and `test_naive_reproducible` in `test_forecasting_models.py` are the tests that would fail if
this contract were broken. When Phase 4 (Monte Carlo) is built, its scenario generator must pass
an equivalent determinism test before being considered done.

## Evaluation philosophy

No forecaster or economics scenario is judged "correct" — only "consistent with its stated
assumptions and calibrated against backtested accuracy metrics." The platform's job is to make
uncertainty and methodology visible (intervals, assumptions, data-quality flags), not to produce
a single confident number. See MODEL_CARD.md for known limitations of every model currently
implemented.
