# ADR-0002: Most Recently Opened Run Continuation

- Status: Accepted
- Scope: Main-menu game continuation

## Decision

An authenticated user can continue the most recently opened run from the main
menu. Opening a run from either new-game or load-game flow updates
`runs.last_opened_at` and `runs.last_opened_attempt_number`. Winning runs remain
eligible until a future run-status design explicitly changes that behavior.

The continuation row is hidden when no eligible run exists and summarizes game
art, run identity and badges, and the latest party without widening the menu.

## Evidence

- Backend fields: `runs.last_opened_at`, `runs.last_opened_attempt_number`
- Backend endpoints: `GET /api/runs/menu-summary`, `POST /api/runs/<run_id>/open`
- Frontend component: `Frontend/src/components/ContinueRunButton.jsx`
