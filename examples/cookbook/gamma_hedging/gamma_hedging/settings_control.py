"""
Runtime-editable hedging thresholds and risk guardrails, changed from the
web dashboard's Settings panel while main.py is already running - no
restart needed, unlike every other config change.

Same thread-safety shape as TagToggleState (gamma_hedging/tag_control.py): the
dashboard's HTTP handler (its own background thread) queues a change here;
main.py's loop thread drains the queue once per tick and applies it to the
live StrategyConfig/KillSwitch/HedgeRateLimiter objects that already exist.

Per-strategy fields (delta_tolerance_lots, high_gamma_threshold, poll
intervals, max_futures_position_lots) are applied via
`dataclasses.replace()` on that strategy's StrategyConfig - it's frozen, so
main.py swaps in a new instance rather than mutating fields in place.
Account-level fields (rate limit, circuit breaker, API error threshold) are
applied by mutating the live KillSwitch/HedgeRateLimiter objects directly -
those are plain (non-frozen) dataclasses already designed to be updated
mid-session (see their own docstrings in gamma_hedging/risk.py and safety.py).
"""

from __future__ import annotations

import threading

# field -> (min, max, is_int). Used both to validate values coming in from
# the UI and to know whether to coerce to int or float. Bounds are meant to
# reject obviously-broken input (negative poll intervals, a zero-width
# circuit breaker window), not to encode "good" trading values - that
# judgment stays with whoever is running the session.
PER_STRATEGY_FIELDS: dict[str, tuple[float, float, bool]] = {
    "delta_tolerance_lots": (0.001, 1000.0, False),
    "high_gamma_threshold": (0.0001, 10.0, False),
    "poll_interval_normal_sec": (1.0, 3600.0, False),
    "poll_interval_high_gamma_sec": (1.0, 3600.0, False),
    "max_futures_position_lots": (1, 100000, True),
}
ACCOUNT_FIELDS: dict[str, tuple[float, float, bool]] = {
    "max_hedge_trades_per_min": (1, 100000, True),
    "circuit_breaker_pct": (0.001, 100.0, False),
    "circuit_breaker_window_sec": (1, 86400, True),
    "max_consecutive_api_errors": (1, 100000, True),
}


class SettingsStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending_strategy: dict[str, dict[str, float]] = {}
        self._pending_account: dict[str, float] = {}

    def set_strategy_field(self, strategy_name: str, field_name: str, raw_value) -> float:
        if field_name not in PER_STRATEGY_FIELDS:
            raise ValueError(f"Unknown strategy setting {field_name!r}")
        lo, hi, is_int = PER_STRATEGY_FIELDS[field_name]
        value = int(float(raw_value)) if is_int else float(raw_value)
        if not (lo <= value <= hi):
            raise ValueError(f"{field_name}={value} out of allowed range [{lo}, {hi}]")
        with self._lock:
            self._pending_strategy.setdefault(strategy_name, {})[field_name] = value
        return value

    def set_account_field(self, field_name: str, raw_value) -> float:
        if field_name not in ACCOUNT_FIELDS:
            raise ValueError(f"Unknown account setting {field_name!r}")
        lo, hi, is_int = ACCOUNT_FIELDS[field_name]
        value = int(float(raw_value)) if is_int else float(raw_value)
        if not (lo <= value <= hi):
            raise ValueError(f"{field_name}={value} out of allowed range [{lo}, {hi}]")
        with self._lock:
            self._pending_account[field_name] = value
        return value

    def drain_pending(self) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
        """Called once per tick by main.py: returns whatever changes have
        been queued since the last call and clears the queue, so each
        change is applied exactly once.
        """
        with self._lock:
            strategy_changes, self._pending_strategy = self._pending_strategy, {}
            account_changes, self._pending_account = self._pending_account, {}
        return strategy_changes, account_changes
