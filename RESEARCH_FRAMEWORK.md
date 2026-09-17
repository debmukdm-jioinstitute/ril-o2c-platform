# Research Framework

## Purpose

This platform exists to demonstrate a methodology, not to ship a finished product. Every module
should be judged on: (1) is the math right, (2) is uncertainty represented honestly, (3) can the
result be reproduced, (4) does it complement rather than duplicate the company's existing LP
optimizer.

## Build order and status

Phases follow the original spec's numbering. This build (across sessions) has completed
Phases 1–4.

| Phase | Scope | Status |
|---|---|---|
| 1 | Architecture, database, synthetic data | ✅ Done |
| 2 | Forecasting engine | ✅ Done |
| 3 | Feedstock economics + switch-point engine | ✅ Done |
| 4 | Monte Carlo / stochastic scenario engine | ✅ Done — ≥10,000 correlated scenarios, EBITDA/revenue/margin/NPV/IRR distributions, probability of threshold breach, downside/upside cases |
| 5 | Capacity expansion financial model | Not started — Phase 4's NPV/IRR use a simplified flat-annuity, all-at-once-capex model; a real ramp-up/phased-capex DCF is the remaining work |
| 6 | Reverse stress testing | Not started — the Monte Carlo engine's `MonteCarloResult.raw` already holds the full scenario population this would search |
| 7 | AI Copilot | Not started |
| 8 | Executive dashboard | Partial — a working forecast + feedstock control-tower view exists (`frontend/app/page.tsx`); not the full spec'd Executive Control Tower (no NPV/IRR/scenario-risk/model-confidence rollup yet — those Monte Carlo outputs exist in the API but aren't wired into the UI yet) |
| 9 | Research Lab | Partial — backtesting is fully implemented and API-accessible; no dedicated Research Lab UI (model comparison, parameter tuning, export) yet |
| 10 | Testing + documentation + deployment | Partial — 74 passing tests for everything built so far, full doc set, Docker Compose for local deployment; no CI pipeline configured yet |

## What "done" means for a phase in this repo

- Real computation, not mocked/hard-coded outputs (spec module 16: no fake intelligence).
- Unit tests that would fail if the logic were wrong (not just "does it run").
- A governance envelope on every model output (spec module 15).
- Synthetic data clearly labeled as such everywhere it surfaces (API responses, UI).
- Documented in METHODOLOGY.md with the actual formulas/algorithms used.

## Known gaps to close in the next phase (capacity expansion financial model, Phase 5)

- `backend/requirements-optional.txt` lists `pymc`/`arviz` — still not installed; Phase 4 didn't
  need them (percentiles come directly off the empirical Monte Carlo distribution, no parametric
  Bayesian fitting), so they remain optional until a module actually needs them.
- `financial/` exists as an empty package (`__init__.py` only) — this is where a proper
  multi-year ramp-up curve and phased capex schedule belong (METHODOLOGY.md §6). It should reuse
  `simulation/financial_mc.py`'s IRR solver (`brentq` over `[-50%, 500%]`, chosen to avoid the
  `(1+r)^-t` blow-up near `-100%`) rather than reimplementing root-finding.
- `simulation/monte_carlo.py` currently supports only `ethane`/`naphtha` as MC feedstocks
  (only feedstocks with a scenario price variable per the spec's variable list). If
  propane/butane MC scenarios are wanted later, that means either adding them as scenario
  variables (extending `DEFAULT_MARKET_CORRELATION`) or deriving them from the crude/naphtha
  block with a documented proxy relationship — not silently reusing naphtha's price.
- Reverse stress testing (Phase 6) is the natural next module after Phase 5, since it operates
  directly on `MonteCarloResult.raw` — no new scenario-generation code needed, just a filter +
  characterization layer (see METHODOLOGY.md §7).

## Reproducibility contract

Every function that involves randomness takes an explicit `seed` (or `random_seed` on a class)
and defaults to `42`. `tests/unit/test_synthetic_generator.py::test_deterministic_given_seed`,
`test_naive_reproducible` in `test_forecasting_models.py`, and
`test_reproducible_given_seed` in both `test_market_scenarios.py` and `test_monte_carlo.py` are
the tests that would fail if this contract were broken.

## Evaluation philosophy

No forecaster or economics scenario is judged "correct" — only "consistent with its stated
assumptions and calibrated against backtested accuracy metrics." The platform's job is to make
uncertainty and methodology visible (intervals, assumptions, data-quality flags), not to produce
a single confident number. See MODEL_CARD.md for known limitations of every model currently
implemented.
