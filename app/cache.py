"""简单 TTL 缓存

Trending 数据 1 小时内基本不会变,加一层 TTL 缓存避免反复抓取 + 翻译。
"""
from __future__ import annotations

import time
from threading import Lock
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, T]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[T]:
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            ts, value = entry
            if time.time() - ts > self._ttl:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: T) -> None:
        with self._lock:
            self._store[key] = (time.time(), value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {"size": len(self._store), "ttl_seconds": self._ttl}
