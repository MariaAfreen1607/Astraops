"""Lightweight in-memory TTL cache for external API responses."""

from __future__ import annotations

import atexit
import json
import time
from pathlib import Path
from threading import Lock
from typing import Any, Optional


class TTLCache:
    """Thread-safe in-memory key/value cache with per-entry TTL."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """Return cached value if present and not expired, else None."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Store *value* under *key* for *ttl* seconds."""
        with self._lock:
            self._store[key] = (value, time.monotonic() + ttl)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        """Return number of non-expired entries."""
        now = time.monotonic()
        with self._lock:
            return sum(1 for _, (_, exp) in self._store.items() if exp > now)


# Module-level singleton shared across the application
cache = TTLCache()



# --- Disk persistence -------------------------------------------------------
# The in-memory cache is fast but dies with the process. On a free-tier host
# that sleeps after inactivity, every wake would re-fetch every upstream feed.
# Values that survive a restart are written to disk as JSON on shutdown and
# reloaded on boot; anything unserialisable is simply skipped.

_DISK = Path(__file__).resolve().parent / ".cache_state.json"


def _persist() -> None:
    try:
        out = {}
        for key, entry in getattr(cache, "_store", {}).items():
            value, expires = entry if isinstance(entry, tuple) else (entry, None)
            if expires is not None and expires < time.time():
                continue
            try:
                payload = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
                json.dumps(payload)
            except Exception:
                continue
            out[key] = {"value": payload, "expires": expires}
        _DISK.write_text(json.dumps(out), encoding="utf-8")
    except Exception:
        pass


atexit.register(_persist)
