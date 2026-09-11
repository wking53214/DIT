import hashlib

from dit import OscillationGuard, TowerConfig, state_digest


def test_state_digest_is_sha256_not_md5():
    """The audit's 'Upgrade State Hashing Primitives'."""
    text = "payload"
    assert state_digest(text) == hashlib.sha256(text.encode()).hexdigest()
    assert len(state_digest(text)) == 64
    assert state_digest(text) != hashlib.md5(text.encode()).hexdigest()


def test_guard_reports_a_repeat():
    guard = OscillationGuard(TowerConfig())
    digest = state_digest("same")
    assert not guard.seen(digest)
    guard.remember(digest)
    assert guard.seen(digest)


def test_guard_evicts_by_size():
    """The audit's 'Unbounded Memory Growth'."""
    guard = OscillationGuard(TowerConfig(loop_cache_entries=8))
    for index in range(100):
        guard.remember(state_digest(str(index)))
    assert len(guard) <= 8
    assert not guard.seen(state_digest("0"))
    assert guard.seen(state_digest("99"))


def test_guard_expires_by_age():
    now = [1000.0]
    guard = OscillationGuard(
        TowerConfig(loop_cache_ttl_seconds=10.0), clock=lambda: now[0]
    )
    guard.remember(state_digest("old"))
    assert guard.seen(state_digest("old"))
    now[0] += 11.0
    assert not guard.seen(state_digest("old"))


def test_reuse_refreshes_recency():
    guard = OscillationGuard(TowerConfig(loop_cache_entries=2))
    guard.remember(state_digest("a"))
    guard.remember(state_digest("b"))
    guard.remember(state_digest("a"))  # a is now the most recent
    guard.remember(state_digest("c"))  # evicts b, not a
    assert guard.seen(state_digest("a"))
    assert not guard.seen(state_digest("b"))


def test_clear_drops_everything():
    guard = OscillationGuard(TowerConfig())
    guard.remember(state_digest("x"))
    guard.clear()
    assert len(guard) == 0
