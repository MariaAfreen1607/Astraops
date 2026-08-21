"""Tests for cache.py — TTLCache hit, miss, expiry, size, and delete."""

from __future__ import annotations

import time

import pytest

from cache import TTLCache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_cache() -> TTLCache:
    """Return a fresh, isolated TTLCache (not the global singleton)."""
    return TTLCache()


# ---------------------------------------------------------------------------
# Miss
# ---------------------------------------------------------------------------

def test_get_missing_key_returns_none():
    c = make_cache()
    assert c.get("nonexistent") is None


# ---------------------------------------------------------------------------
# Hit
# ---------------------------------------------------------------------------

def test_set_and_get_returns_value():
    c = make_cache()
    c.set("k", {"data": 42}, ttl=60)
    assert c.get("k") == {"data": 42}


def test_set_overwrites_existing_key():
    c = make_cache()
    c.set("k", "first", ttl=60)
    c.set("k", "second", ttl=60)
    assert c.get("k") == "second"


def test_different_keys_are_independent():
    c = make_cache()
    c.set("a", 1, ttl=60)
    c.set("b", 2, ttl=60)
    assert c.get("a") == 1
    assert c.get("b") == 2


# ---------------------------------------------------------------------------
# Expiry
# ---------------------------------------------------------------------------

def test_expired_entry_returns_none():
    c = make_cache()
    c.set("k", "value", ttl=1)
    # Manually backdate the expiry to force immediate expiration without sleeping.
    with c._lock:
        val, _ = c._store["k"]
        c._store["k"] = (val, time.monotonic() - 0.001)
    assert c.get("k") is None


def test_expired_entry_is_evicted_from_store():
    """get() must delete the expired entry, not just return None."""
    c = make_cache()
    c.set("k", "value", ttl=1)
    with c._lock:
        val, _ = c._store["k"]
        c._store["k"] = (val, time.monotonic() - 0.001)
    c.get("k")  # triggers eviction
    with c._lock:
        assert "k" not in c._store


def test_not_yet_expired_entry_is_returned():
    c = make_cache()
    c.set("k", "alive", ttl=3600)
    assert c.get("k") == "alive"


# ---------------------------------------------------------------------------
# Size
# ---------------------------------------------------------------------------

def test_size_counts_only_live_entries():
    c = make_cache()
    c.set("live", "yes", ttl=3600)
    c.set("dead", "no", ttl=1)
    # Backdate the dead entry.
    with c._lock:
        val, _ = c._store["dead"]
        c._store["dead"] = (val, time.monotonic() - 0.001)
    assert c.size() == 1


def test_size_zero_on_empty_cache():
    c = make_cache()
    assert c.size() == 0


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

def test_delete_removes_key():
    c = make_cache()
    c.set("k", "v", ttl=60)
    c.delete("k")
    assert c.get("k") is None


def test_delete_nonexistent_key_is_a_noop():
    c = make_cache()
    c.delete("never_stored")  # must not raise


# ---------------------------------------------------------------------------
# Clear
# ---------------------------------------------------------------------------

def test_clear_empties_all_entries():
    c = make_cache()
    c.set("a", 1, ttl=60)
    c.set("b", 2, ttl=60)
    c.clear()
    assert c.size() == 0
    assert c.get("a") is None
    assert c.get("b") is None


# ---------------------------------------------------------------------------
# Arbitrary value types
# ---------------------------------------------------------------------------

def test_stores_various_python_types():
    c = make_cache()
    c.set("list", [1, 2, 3], ttl=60)
    c.set("dict", {"x": 1}, ttl=60)
    c.set("none_val", None, ttl=60)
    # None is a valid value; get() returns None for both missing and None-valued keys —
    # that's acceptable behaviour documented implicitly by the implementation.
    assert c.get("list") == [1, 2, 3]
    assert c.get("dict") == {"x": 1}
