# Fix Proposal: `_ensure_badge_schema` overhead + `get_runs()` N+1

Proposal only — nothing has been changed. Two fixes, ordered by risk: a small safe one first, a bigger structural one second. Digging into the exact code made the problem worse than first estimated — worth reading the "How bad it actually is" section before the fixes.

## How bad it actually is

Inside `get_runs()`'s per-run loop, three separate things each independently look up the same attempt, and each one drags in `_ensure_badge_schema`:

1. `get_party_for_attempt(conn, run_id, latest_attempt)` — looks up `attempt_id`, then calls `_ensure_badge_schema` (~10 queries) before running its actual party query.
2. `get_attempt_session_stats(conn, run_id, latest_attempt)` — looks up `attempt_id` *again* (duplicate query), then calls `_get_attempt_badge_ids`, which calls `_ensure_badge_schema` *again* (~10 more queries).
3. `get_runs()` itself then does a third `attempt_id` lookup directly, followed by a direct call to `_get_attempt_badge_ids` — a third `_ensure_badge_schema` call (~10 more queries).

So it's not "N+1," it's closer to 3-4 schema-check bursts of ~10 queries each, per run, on top of the real data queries. For a user with 10 runs, that's 300+ throwaway queries just re-verifying that tables/columns/indexes exist — before a single real row of party data comes back.

## Fix 1 (small, safe): memoize the `_ensure_*_schema` checks per process

All four bootstrap functions (`_ensure_auth_schema`, `_ensure_badge_schema`, `_ensure_bonus_locations_schema`, `_ensure_contact_reports_schema`) do real work exactly once — after the first successful run, the checks always come back "already exists." The fix is a guard flag so each function's body only executes once per process (i.e. once per gunicorn worker, not once per request):

```python
_schema_ready = {'auth': False, 'badge': False, 'bonus_locations': False, 'contact_reports': False}

def _ensure_badge_schema(conn):
    if _schema_ready['badge']:
        return
    # ...existing body, unchanged...
    conn.commit()
    _schema_ready['badge'] = True
```

Same pattern applied to the other three. This is a handful of lines added to four functions, doesn't change any function signature or caller, and doesn't touch query logic at all — low risk, and it alone removes the dominant cost identified above (roughly 30-40 wasted queries per run collapses to effectively zero after the first request each worker process handles).

**Trade-off to know about:** if the schema changes out-of-band while a worker is already running (e.g. a manual `ALTER TABLE` run directly against Supabase), that worker won't notice until it restarts. Normal and acceptable for this kind of idempotent bootstrap check, but worth knowing.

## Fix 2 (bigger, more care needed): batch `get_runs()` instead of looping per run

This is a real restructure of the query shape, not just a guard clause — good candidate to do *after* Fix 1, and to lean on the new pytest suite (`test_core_mutations.py`) to confirm behavior doesn't regress, since this touches the most-used endpoint in the app.

Shape of the fix:

1. **Get every run's `attempt_id` in the same query that already computes `latest_attempt`**, instead of three separate follow-up lookups. The existing aggregating subquery can be extended to also return the attempt row for the latest attempt (e.g. a `LEFT JOIN LATERAL ... ORDER BY attempt_number DESC LIMIT 1`), which removes all three redundant `attempt_id` lookups per run in one move.

2. **One batched party query for every run on the page**, instead of one call to `get_party_for_attempt` per run:
   ```sql
   SELECT p.attempt_id, p.party_slot, p.pokemon_id, pb.species_id, s.name AS species_name, ...
   FROM party p
   JOIN pokebank pb ON p.pokemon_id = pb.pokemon_id
   JOIN species s ON pb.species_id = s.species_id
   -- (same stat/type/ability lateral joins as today)
   WHERE p.attempt_id IN (%s, %s, ...)
   ORDER BY p.attempt_id, p.party_slot
   ```
   Group the results by `attempt_id` in Python afterward and attach each run's slice.

3. **One batched stats query** (status counts + trainers-defeated), grouped by `attempt_id IN (...)` instead of once per run, assembled in Python into the same shape `get_attempt_session_stats` returns today.

4. **One batched badge-ids query**: `SELECT attempt_id, badge_id FROM attempt_badges WHERE attempt_id IN (...)`, grouped by `attempt_id` in Python.

Net effect: `get_runs()` goes from roughly `4N` queries (each multiplied by the schema-check overhead before Fix 1) down to about 5 queries total, regardless of how many runs the user has. Combined with Fix 1, that's the difference between 300+ queries and roughly 5 for the runs list page.

## Suggested order

Do Fix 1 first — it's small, low-risk, and removes most of the pain on its own with almost no chance of introducing a bug. Then decide whether Fix 2's batching is worth the larger diff; it's the "correct" fix and matters more as the number of runs per user grows, but Fix 1 alone likely gets load time into acceptable territory for how this app is actually used today (a handful of runs per player, not hundreds).
