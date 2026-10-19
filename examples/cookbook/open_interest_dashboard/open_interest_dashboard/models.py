"""Plain data containers shared by the scoring, dashboard and order modules."""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


class Direction(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass
class StockState:
    symbol: str
    weight: float  # percent weight in NIFTY 50
    ref_id: int | None = None
    last_price: float | None = None   # rupees
    base_price: float | None = None   # first price seen, rupees
    last_volume: int | None = None
    pressure: deque[float] = field(default_factory=lambda: deque(maxlen=24))
    volume_deltas: deque[int] = field(default_factory=lambda: deque(maxlen=60))
    price_points: deque[tuple[float, float]] = field(default_factory=lambda: deque(maxlen=120))


@dataclass
class IndexState:
    symbol: str = "NIFTY"
    last_price: float | None = None  # rupees
    base_price: float | None = None
    points: deque[tuple[float, float]] = field(default_factory=lambda: deque(maxlen=120))


@dataclass
class OptionContract:
    """One CE/PE row of the option chain. Prices are rupees, quantities are units."""
    ref_id: int
    option_type: str  # "CE" or "PE"
    strike: float
    ltp: float
    lot_size: int
    delta: float
    gamma: float
    theta: float
    volume: int
    oi: int
    previous_oi: int

    @property
    def oi_change(self) -> int:
        return self.oi - self.previous_oi

    @property
    def lot_cost(self) -> float:
        return self.ltp * self.lot_size


@dataclass
class MarketReading:
    """Result of one evaluation: bias score plus the best-ranked candidate contract."""
    direction: Direction
    score: float           # blended bias score in [-1, 1]
    pressure_score: float  # constituent pressure in [-1, 1]
    oi_score: float        # OI-change score in [-1, 1]
    reason: str
    contract: OptionContract | None = None
    qty: int = 0           # units for one lot if the affordability/risk filter passes


@dataclass
class RuntimeStats:
    stock_ticks: int = 0
    index_ticks: int = 0
    option_ticks: int = 0
    last_option_at: float | None = None
    last_stock_at: float | None = None
    last_index_at: float | None = None
    socket_status: str = "starting"
    events: deque[str] = field(default_factory=lambda: deque(maxlen=8))


@dataclass
class WebDashboardState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    payload: dict[str, Any] = field(default_factory=dict)

    def update(self, payload: dict[str, Any]) -> None:
        with self.lock:
            self.payload = payload

    def read(self) -> dict[str, Any]:
        with self.lock:
            return dict(self.payload)


def rupees(paise_value: Any) -> float:
    """SDK prices arrive as integer paise; return rupees (0.0 for missing values)."""
    if paise_value is None:
        return 0.0
    try:
        return float(paise_value) / 100.0
    except (TypeError, ValueError):
        return 0.0


def paise(rupee_value: float) -> int:
    return int(round(rupee_value * 100))


def first_attr(obj: Any, names: Iterable[str], default: Any = None) -> Any:
    """Return the first present attribute/key; SDK messages are objects, tests may pass dicts."""
    if isinstance(obj, dict):
        for name in names:
            if name in obj:
                return obj[name]
        return default
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return default
