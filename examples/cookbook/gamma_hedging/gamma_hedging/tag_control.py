"""
Runtime control plane for attaching gamma-hedging to a strategy discovered
live on the broker (via NubraClient.discover_tagged_strategies()),
toggled on/off from the web dashboard while main.py is already running.

This is intentionally a thin, thread-safe shared object: the web dashboard's
HTTP handler (running in its own background thread) writes to it when the
user flips a toggle; main.py's loop thread reads it once per tick to decide
which discovered strategies to start or stop hedging. Neither side blocks
the other beyond a short lock hold.
"""

from __future__ import annotations

import threading

from .nubra_client import DiscoveredStrategy


class TagToggleState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._enabled: set[str] = set()
        self._discovered: dict[str, DiscoveredStrategy] = {}

    def enable(self, tag: str) -> None:
        with self._lock:
            self._enabled.add(tag)

    def disable(self, tag: str) -> None:
        with self._lock:
            self._enabled.discard(tag)

    def enabled_tags(self) -> set[str]:
        with self._lock:
            return set(self._enabled)

    def set_discovered(self, discovered: dict[str, DiscoveredStrategy]) -> None:
        with self._lock:
            self._discovered = discovered
            # A tag that no longer nets to a live position (e.g. squared off
            # since the last discovery pass) can't stay "enabled" - nothing
            # for main.py to attach or keep hedging.
            self._enabled &= discovered.keys()

    def discovered_tags(self) -> dict[str, DiscoveredStrategy]:
        with self._lock:
            return dict(self._discovered)
