"""Plain-text terminal dashboard (ANSI clear-screen redraw, no extra dependencies)."""
from __future__ import annotations

import shutil
import sys
import time
from datetime import datetime
from typing import Any

from .models import MarketReading, OptionContract, RuntimeStats, StockState
from .pressure import top_pressure


def score_bar(value: float, width: int = 18) -> str:
    """Centered bar: '+' fills right of the midpoint for positive scores, '-' fills left for negative."""
    value = max(-1.0, min(1.0, value))
    mid = width // 2
    fill = min(mid, int(abs(value) * mid))
    if value > 0:
        return "." * mid + "+" * fill + " " * (mid - fill)
    if value < 0:
        return " " * (mid - fill) + "-" * fill + "." * mid
    return "." * width


def age_text(timestamp: float | None) -> str:
    return "never" if timestamp is None else f"{time.time() - timestamp:0.0f}s ago"


def dashboard_lines(
    reading: MarketReading,
    states: dict[int, StockState],
    contracts: list[OptionContract],
    stats: RuntimeStats,
    orders_sent: int,
    args: Any,
) -> list[str]:
    columns = shutil.get_terminal_size((120, 32)).columns
    width = min(max(columns, 96), 140)
    rule = "-" * width
    ce_count = sum(1 for c in contracts if c.option_type == "CE")
    pe_count = sum(1 for c in contracts if c.option_type == "PE")
    feed = "OK" if contracts else "WAITING"
    orders = "ON" if args.place_orders else "DRY-RUN"
    label = reading.direction.value
    if reading.contract and reading.qty > 0:
        label = f"{label} {reading.contract.option_type} {reading.contract.strike:g}"

    lines = [
        rule,
        f"NIFTY OPEN INTEREST DASHBOARD  {datetime.now():%H:%M:%S}  ENV={args.env}  EXPIRY={args.expiry}  "
        f"ORDERS={orders}  MODE={args.order_mode.upper()}",
        rule,
        f"READING {label:<22} BIAS {reading.score:+.3f} {score_bar(reading.score)}  {reading.reason[:46]}",
        f"PRESSURE {reading.pressure_score:+.3f} {score_bar(reading.pressure_score)}  "
        f"OI {reading.oi_score:+.3f} {score_bar(reading.oi_score)}  "
        f"OPTION_FEED={feed} CE/PE={ce_count}/{pe_count} age={age_text(stats.last_option_at)}",
        f"FEEDS   stock_ticks={stats.stock_ticks} age={age_text(stats.last_stock_at)}  "
        f"index_ticks={stats.index_ticks}  orders_sent={orders_sent}/{args.max_orders}  capital={args.capital:.0f}",
        rule,
    ]

    c = reading.contract
    if c:
        lines.append(
            f"CANDIDATE {c.option_type:<2} strike={c.strike:g} ltp={c.ltp:.2f} delta={c.delta:+.3f} "
            f"gamma={c.gamma:.5f} vol={c.volume} oi_chg={c.oi_change:+d} lot_cost={c.lot_cost:.2f} qty={reading.qty}"
        )
    else:
        lines.append("CANDIDATE none yet - needs agreeing pressure and OI scores plus an affordable positive-gamma contract")

    lines.append(rule)
    lines.append("TOP NIFTY PRESSURE")
    rows = top_pressure(states)
    for symbol, weight, avg in rows:
        lines.append(f"  {symbol:<12} w={weight:>5.2f}% pressure={avg:+.3f} {score_bar(avg, 14)}")
    if not rows:
        lines.append("  waiting for stock order-book packets")

    lines.append(rule)
    lines.append("EVENTS")
    for event in stats.events:
        lines.append(f"  {event[:width - 4]}")
    if not stats.events:
        lines.append("  no events yet")
    return lines[:31]


def render_dashboard(*args: Any) -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write("\n".join(dashboard_lines(*args)))
    sys.stdout.write("\n")
    sys.stdout.flush()
