# Legacy and Redundancy Removal Plan

This plan is intentionally conservative: remove low-risk legacy first, then medium-risk drift, then high-risk migrations with rollback checkpoints.

## Goals

- Reduce dead code and stale docs that slow delivery.
- Eliminate duplicate and obsolete configuration surfaces.
- Keep behavior stable while tightening reliability and security.

## Critical Review of Options

### Auth Configuration Drift

Option A: remove unused auth flags (`API_KEY_ENABLED`, `API_SECRET_KEY`) now.
- Pros: smaller config surface and less confusion.
- Cons: potential breaking change for operators expecting those keys.

Option B: wire flags into auth flow, then deprecate.
- Pros: backward-compatible transition.
- Cons: adds temporary complexity.

Decision: Option B for one release cycle, then remove.

### SQL Placeholder Strategy

Option A: immediate global migration to one placeholder style.
- Pros: clean long-term state.
- Cons: high blast radius and regression risk.

Option B: keep compatibility translation, migrate incrementally with tests.
- Pros: safer rollout with smaller PRs.
- Cons: temporary dual behavior.

Decision: Option B.

### Query Module Decomposition

Option A: split `queries.py` now.
- Pros: cleaner architecture.
- Cons: high merge conflict and regression risk during active fixes.

Option B: freeze public function signatures, then split by domain.
- Pros: lower migration risk.
- Cons: slower architecture cleanup.

Decision: Option B.

## Phase 1 (Immediate, Low Risk)

1. Remove duplicate dependencies.
- Status: completed
- Change: duplicate `httpx` entry removed from `requirements.txt`.

2. Align docs to current repository layout.
- Status: completed
- Change: updated project structure and data-source extension guidance in `README.md`.

3. Remove stale compose flags and worker command drift.
- Status: completed
- Change: removed `--reload` from API production command and switched worker startup to `python worker.py`.

## Phase 2 (Near-Term, Medium Risk)

1. Consolidate auth-related settings.
- Current drift: `API_KEY_ENABLED` and `API_SECRET_KEY` exist but are not enforced in auth flow.
- Action: either wire into `api/v1/dependencies/auth.py` or remove from config and `.env.example`.

2. Standardize table naming.
- Current drift: some code paths reference `stock_prices` while canonical storage is `yfinance_ohlcv`.
- Action: centralize table constants and migrate all references.

3. Replace broad exception swallowing in dashboard.
- Current drift: multiple bare `except:` blocks in `app.py` hide actionable failures.
- Action: replace with typed exceptions and structured warning logs.

## Phase 3 (Planned, Higher Risk)

1. Reduce over-broad shared query surface.
- Action: split `modules/database/queries.py` by domain (market, features, SEC, ML).
- Benefit: improves ownership and lowers accidental coupling.

2. Introduce split dependency sets.
- Action: maintain service-specific requirement files (`api`, `worker`, `dashboard`, `dev`).
- Benefit: slimmer images and faster install/CI times.

3. Remove compatibility placeholder translation once all SQL is standardized.
- Current state: PostgreSQL now translates `?` placeholders to `%s` for compatibility.
- Action: gradually migrate all SQL to one style and delete translation shim.

## Rollback Strategy

- Keep each phase in separate PRs.
- Tag release before Phase 2 and Phase 3 starts.
- Use canary deployment for worker and API changes.
- Retain one release cycle of backward compatibility for env vars and schemas.

## Execution Gates (Must Pass)

1. `docker compose config` succeeds.
2. `docker compose up --build` reaches healthy API and Redis/Postgres healthy state.
3. API smoke tests pass:
- `GET /health`
- `GET /ready`
- Representative data endpoint
- Representative portfolio endpoint
4. Worker process remains running and schedules jobs without import/runtime errors.
5. Dashboard container starts (profile enabled).
6. Negative auth check passes on protected endpoint without API key.

If any gate fails, stop rollout, capture logs, and patch before proceeding.
