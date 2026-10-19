"""Historical replay of the long future + short ATM calls hedge.

Fetches three already-known historical series with ``MarketData.historical_data``
(future close, call close + delta, equity close), aligns them bar by bar and
replays the same pure functions the live runner uses (``hedging.logic``). No
orders are placed; the only SDK call is the historical fetch.

A replay uses the bar close as the fill price with no slippage, spread or
brokerage model, and one call contract for the whole window. It checks the
hedge and exit rules; it is not a prediction of live results.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import logic


@dataclass(frozen=True)
class BacktestConfig:
    future_symbol: str  # exact historical futures contract name
    call_symbol: str  # exact historical ATM call contract name
    equity_symbol: str
    lot_size: int
    pnl_target: float
    pnl_stop_loss: float
    start_date: str
    end_date: str
    exchange: str = "NSE"
    num_short_calls: int = 2
    future_lots: int = 1
    hedge_trigger_pct: float = 1.5
    interval: str = "5m"
    starting_capital: float = 0.0  # chart offset only; never used in any decision

    def validate(self) -> None:
        if self.pnl_target <= 0:
            raise SystemExit(f"--pnl-target must be positive, got {self.pnl_target}")
        if self.pnl_stop_loss > 0:
            raise SystemExit(f"--pnl-stop-loss must be zero or negative, got {self.pnl_stop_loss}")
        if self.lot_size < 1 or self.num_short_calls < 1 or self.future_lots < 1:
            raise SystemExit("--lot-size, --short-calls and --future-lots must be at least 1")


@dataclass(frozen=True)
class Bar:
    timestamp_ns: int
    future_close: float  # rupees
    call_close: float  # rupees
    call_delta: float
    equity_close: float  # rupees

    @property
    def timestamp_iso(self) -> str:
        return datetime.fromtimestamp(self.timestamp_ns / 1e9, tz=timezone.utc).isoformat()


@dataclass(frozen=True)
class CurvePoint:
    timestamp: str
    total_pnl: float
    equity_hedge_shares: float
    net_delta: Optional[float]


@dataclass(frozen=True)
class HedgeTrade:
    timestamp: str
    side: str
    qty: int
    price: float
    net_delta_before: float
    net_delta_after: float


@dataclass
class BacktestResult:
    config: BacktestConfig
    entry_timestamp: str
    entry_future_price: float
    entry_call_price: float
    entry_call_delta: float
    entry_equity_price: float
    curve: List[CurvePoint]
    trades: List[HedgeTrade]
    exit_timestamp: Optional[str]
    exit_reason: Optional[str]
    exit_pnl: Optional[float]
    unresolved: bool
    final_pnl: float
    max_drawdown: float
    bars_used: int = field(default=0)

    @property
    def target_hit(self) -> Optional[bool]:
        return self.exit_reason.startswith("pnl_target_hit") if self.exit_reason else None


# ---- fetching ------------------------------------------------------------------------------

_ISO_Z = "%Y-%m-%dT%H:%M:%S.000Z"


def to_utc_iso(value: str, end_of_session: bool = False) -> str:
    """Accept YYYY-MM-DD or a full ISO string and return the UTC string the API expects.

    A bare date maps to the NSE session in UTC: 03:45 (09:15 IST) to 10:00 (15:30 IST).
    """
    if "T" in value:
        return value
    day = datetime.strptime(value, "%Y-%m-%d")
    hour, minute = (10, 0) if end_of_session else (3, 45)
    return day.replace(hour=hour, minute=minute).strftime(_ISO_Z)


def _series(response, symbol: str, field_name: str) -> Dict[int, float]:
    """``{timestamp_ns: value}`` for one symbol/field. Price fields arrive as paise."""
    out: Dict[int, float] = {}
    for chart_data in response.result or []:
        for entry in chart_data.values or []:
            chart = entry.get(symbol)
            if chart is None:
                continue
            for point in getattr(chart, field_name, None) or []:
                if point.timestamp is None or point.value is None:
                    continue
                value = float(point.value)
                out[int(point.timestamp)] = value if field_name == "delta" else value / 100.0
    return out


def fetch_bars(market_data, cfg: BacktestConfig) -> List[Bar]:
    start, end = to_utc_iso(cfg.start_date), to_utc_iso(cfg.end_date, end_of_session=True)

    def query(kind: str, symbol: str, fields: List[str]) -> dict:
        return {
            "exchange": cfg.exchange,
            "type": kind,
            "values": [symbol],
            "fields": fields,
            "startDate": start,
            "endDate": end,
            "interval": cfg.interval,
            "intraDay": False,
            "realTime": False,
        }

    response = market_data.historical_data(
        [
            query("FUT", cfg.future_symbol, ["close"]),
            query("OPT", cfg.call_symbol, ["close", "delta"]),
            query("STOCK", cfg.equity_symbol, ["close"]),
        ]
    )
    # historical_data() returns (does not raise) a validation error for a bad payload.
    if response is None or not hasattr(response, "result"):
        raise SystemExit(f"Historical request failed or returned nothing: {response}")
    return align_bars(
        _series(response, cfg.future_symbol, "close"),
        _series(response, cfg.call_symbol, "close"),
        _series(response, cfg.call_symbol, "delta"),
        _series(response, cfg.equity_symbol, "close"),
    )


def align_bars(
    future_close: Dict[int, float],
    call_close: Dict[int, float],
    call_delta: Dict[int, float],
    equity_close: Dict[int, float],
) -> List[Bar]:
    """Keep only timestamps present in all four series."""
    common = set(future_close) & set(call_close) & set(call_delta) & set(equity_close)
    return [
        Bar(ts, future_close[ts], call_close[ts], call_delta[ts], equity_close[ts])
        for ts in sorted(common)
    ]


# ---- simulation ----------------------------------------------------------------------------


def simulate(bars: List[Bar], cfg: BacktestConfig) -> BacktestResult:
    if len(bars) < 2:
        raise ValueError(
            f"Need at least 2 aligned bars (entry + one replay bar), got {len(bars)}. "
            "Check the symbols, date range and interval."
        )

    fut_qty = float(logic.lots_to_shares(cfg.future_lots, cfg.lot_size))
    call_qty_each = float(logic.lots_to_shares(1, cfg.lot_size))
    total_call_qty = call_qty_each * cfg.num_short_calls

    entry = bars[0]  # entry at the first bar where all three prices are known
    hedge_shares, avg_price, realized = 0.0, 0.0, 0.0
    last_hedge_price = entry.equity_close

    trades: List[HedgeTrade] = []
    curve: List[CurvePoint] = []
    last_net_delta: Optional[float] = None
    exit_ts = exit_reason = None
    exit_pnl: Optional[float] = None
    unresolved = True
    bars_used = 0

    for i, bar in enumerate(bars):
        bars_used = i + 1
        checked = False
        if i > 0 and logic.should_check_rehedge(last_hedge_price, bar.equity_close, cfg.hedge_trigger_pct):
            checked = True
            net_delta = logic.compute_net_delta_shares(
                fut_qty, [bar.call_delta] * cfg.num_short_calls, [call_qty_each] * cfg.num_short_calls, hedge_shares
            )
            last_net_delta = net_delta
            hedge = logic.compute_hedge_order(net_delta)
            if hedge is not None:
                side, qty = hedge
                signed = qty if side == "BUY" else -qty
                hedge_shares, avg_price, realized = logic.apply_hedge_fill(
                    prev_shares=hedge_shares,
                    avg_hedge_price=avg_price,
                    realized_pnl=realized,
                    side=side,
                    qty=qty,
                    fill_price=bar.equity_close,
                )
                trades.append(
                    HedgeTrade(bar.timestamp_iso, side, qty, bar.equity_close, net_delta, net_delta + signed)
                )
            last_hedge_price = bar.equity_close

        total_pnl = logic.mark_to_market_pnl(
            entry_future_price=entry.future_close,
            future_price=bar.future_close,
            future_qty_shares=fut_qty,
            entry_call_price=entry.call_close,
            call_price=bar.call_close,
            short_call_qty_shares=total_call_qty,
            equity_hedge_shares=hedge_shares,
            equity_avg_hedge_price=avg_price,
            equity_price=bar.equity_close,
            realized_hedge_pnl=realized,
        )
        curve.append(
            CurvePoint(
                bar.timestamp_iso,
                total_pnl,
                hedge_shares,
                last_net_delta if checked else (curve[-1].net_delta if curve else None),
            )
        )
        should_exit, reason = logic.evaluate_exit(total_pnl, cfg.pnl_target, cfg.pnl_stop_loss)
        if should_exit:
            exit_ts, exit_reason, exit_pnl, unresolved = bar.timestamp_iso, reason, total_pnl, False
            break

    return BacktestResult(
        config=cfg,
        entry_timestamp=entry.timestamp_iso,
        entry_future_price=entry.future_close,
        entry_call_price=entry.call_close,
        entry_call_delta=entry.call_delta,
        entry_equity_price=entry.equity_close,
        curve=curve,
        trades=trades,
        exit_timestamp=exit_ts,
        exit_reason=exit_reason,
        exit_pnl=exit_pnl,
        unresolved=unresolved,
        final_pnl=curve[-1].total_pnl,
        max_drawdown=logic.max_drawdown([p.total_pnl for p in curve]),
        bars_used=bars_used,
    )


def run_backtest(market_data, cfg: BacktestConfig) -> BacktestResult:
    return simulate(fetch_bars(market_data, cfg), cfg)
