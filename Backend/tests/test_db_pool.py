"""
Regression test for the lazy connection-pool initialization race.

Concurrent first requests used to each construct a ThreadedConnectionPool;
the losing pool's connections then failed putconn against the surviving pool
with "trying to put unkeyed connection", leaking the connection. Observed
live on 2026-08-24 when the attempt page fired ~20 parallel requests at a
cold server.
"""
import threading

import api as api_module


def test_burst_over_maxconn_queues_instead_of_failing(pg_uri, monkeypatch, _schema_initialized):
    """A burst larger than maxconn must all succeed, not raise 'pool exhausted'.

    The attempt page opens with ~20 parallel party requests against a pool of
    10, which returned 500s until borrowers were gated on a semaphore.
    """
    monkeypatch.setenv("DATABASE_URL", pg_uri)
    monkeypatch.setattr(api_module, "_db_pool", None)
    monkeypatch.setattr(api_module, "_db_pool_slots", threading.Semaphore(api_module._DB_POOL_MAXCONN))

    burst = api_module._DB_POOL_MAXCONN * 2
    statuses = []
    errors = []
    start = threading.Barrier(burst)
    client = api_module.app.test_client()

    def hit():
        try:
            start.wait(timeout=10)
            statuses.append(client.get("/api/games").status_code)
        except Exception as exc:  # pragma: no cover - only on regression
            errors.append(exc)

    threads = [threading.Thread(target=hit) for _ in range(burst)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    try:
        assert not errors
        assert statuses == [200] * burst
    finally:
        if api_module._db_pool is not None:
            api_module._db_pool.closeall()
        api_module._db_pool = None


def test_concurrent_pool_init_returns_one_shared_pool(pg_uri, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg_uri)
    monkeypatch.setattr(api_module, "_db_pool", None)

    pools = []
    errors = []
    start = threading.Barrier(12)

    def grab():
        try:
            start.wait(timeout=10)
            pools.append(api_module._get_db_pool())
        except Exception as exc:  # pragma: no cover - only on regression
            errors.append(exc)

    threads = [threading.Thread(target=grab) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    try:
        assert not errors
        assert len(pools) == 12
        # Every caller must observe the same pool instance.
        assert len({id(p) for p in pools}) == 1

        # A connection borrowed from that pool must be returnable -- this is
        # the putconn path that raised PoolError before the fix.
        pool = pools[0]
        conn = pool.getconn()
        pool.putconn(conn)
    finally:
        for pool in {id(p): p for p in pools}.values():
            pool.closeall()
        api_module._db_pool = None
