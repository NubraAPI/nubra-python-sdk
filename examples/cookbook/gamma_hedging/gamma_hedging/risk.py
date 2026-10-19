"""Guardrails between "the hedging math says trade N lots" and "an order goes out".

A per-minute rate limiter and an absolute position-size cap. The kill switch
(repeated API errors / abnormal spot move) lives in `gamma_hedging.safety`.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger("gamma_hedging.risk")


@dataclass
class HedgeRateLimiter:
    """Caps how many hedge trades can be placed in any trailing 60s window."""

    max_per_minute: int
    _timestamps: deque = field(default_factory=deque)

    def allow(self, now: float) -> bool:
        self._prune(now)
        return len(self._timestamps) < self.max_per_minute

    def record(self, now: float) -> None:
        self._timestamps.append(now)

    def _prune(self, now: float) -> None:
        cutoff = now - 60.0
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def slots_used(self, now: float) -> int:
        self._prune(now)
        return len(self._timestamps)


def clamp_to_position_cap(current_lots: int, desired_trade_lots: int, cap_lots: int) -> tuple[int, str | None]:
    """Shrink a proposed trade, if needed, so the resulting absolute futures
    position never exceeds `cap_lots`. Returns `(clamped_trade_lots, warning_or_none)`.
    """
    if desired_trade_lots == 0:
        return 0, None

    resulting = current_lots + desired_trade_lots
    if abs(resulting) <= cap_lots:
        return desired_trade_lots, None

    clamped_resulting = cap_lots if resulting > cap_lots else -cap_lots
    clamped_trade = clamped_resulting - current_lots
    warning = (
        f"Hedge trade clamped from {desired_trade_lots:+d} to {clamped_trade:+d} lots to keep the "
        f"futures position within MAX_FUTURES_POSITION_LOTS={cap_lots} (current position "
        f"{current_lots:+d} lots)."
    )
    logger.warning(warning)
    return clamped_trade, warning
