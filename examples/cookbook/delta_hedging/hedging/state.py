"""Durable state for one running delta hedge.

Persisted as JSON after every mutation so that a restart does not lose track of
an open position: on startup the runner loads this file and, if the status is
still ``OPEN``, resumes monitoring instead of re-entering. Dry runs never read
or write this file. Prices are rupees.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import logic

STATUS_PENDING_ENTRY = "PENDING_ENTRY"
STATUS_OPEN = "OPEN"
STATUS_EXITING = "EXITING"
STATUS_CLOSED = "CLOSED"

DEFAULT_STATE_DIR = Path(__file__).resolve().parent.parent / "state"


def state_file_path(symbol: str, state_dir: Path = DEFAULT_STATE_DIR) -> Path:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", symbol.strip().upper())
    return Path(state_dir) / f"hedge_state_{slug}.json"


@dataclass
class PositionState:
    symbol: str
    exchange: str = "NSE"
    status: str = STATUS_PENDING_ENTRY

    future_ref_id: Optional[int] = None
    future_qty_lots: int = 0
    future_lot_size: int = 0

    call_ref_ids: List[int] = field(default_factory=list)  # one entry per short call lot
    call_qty_lots_each: int = 1
    call_strike: Optional[float] = None
    call_lot_size: int = 0

    equity_ref_id: Optional[int] = None
    equity_hedge_shares: int = 0
    equity_avg_hedge_price: float = 0.0

    strategy_intent_order_id: Optional[int] = None

    entry_timestamp: Optional[str] = None
    entry_underlying_price: Optional[float] = None
    last_hedge_underlying_price: Optional[float] = None

    # Entry prices (rupees); used for paper PnL in dry runs.
    entry_future_price: Optional[float] = None
    entry_call_price: Optional[float] = None

    cumulative_hedge_realized_pnl: float = 0.0
    hedge_trades: List[Dict[str, Any]] = field(default_factory=list)

    exit_timestamp: Optional[str] = None
    exit_reason: Optional[str] = None

    def record_hedge_trade(
        self,
        *,
        timestamp: str,
        side: str,
        qty: int,
        price: Optional[float],
        underlying_price: float,
        net_delta_before: float,
        net_delta_after: float,
    ) -> None:
        self.hedge_trades.append(
            {
                "timestamp": timestamp,
                "side": side,
                "qty": qty,
                "price": price,
                "underlying_price": underlying_price,
                "net_delta_before": net_delta_before,
                "net_delta_after": net_delta_after,
            }
        )
        if price is not None:
            new_shares, new_avg, new_realized = logic.apply_hedge_fill(
                prev_shares=self.equity_hedge_shares,
                avg_hedge_price=self.equity_avg_hedge_price,
                realized_pnl=self.cumulative_hedge_realized_pnl,
                side=side,
                qty=qty,
                fill_price=price,
            )
            self.equity_hedge_shares = int(new_shares)
            self.equity_avg_hedge_price = new_avg
            self.cumulative_hedge_realized_pnl = new_realized
        else:
            self.equity_hedge_shares += qty if side == "BUY" else -qty
        self.last_hedge_underlying_price = underlying_price

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PositionState":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, default=str)
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path) -> Optional["PositionState"]:
        path = Path(path)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))
