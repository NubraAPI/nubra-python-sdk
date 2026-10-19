"""NIFTY 50 constituent pressure: order-book imbalance, LTP momentum and volume impulse."""
from __future__ import annotations

import math
import time
from typing import Any

from .config import BOOK_LEVELS, BOOK_WEIGHT, MOMENTUM_GAIN, MOMENTUM_WEIGHT, VOLUME_WEIGHT
from .models import IndexState, StockState, first_attr, rupees


def stock_pressure(msg: Any, state: StockState) -> float:
    """Score one order-book message in [-1, 1] (positive = buy-side pressure) and update `state`."""
    ltp = rupees(first_attr(msg, ["last_traded_price", "ltp"]))
    volume = int(first_attr(msg, ["volume"], 0) or 0)
    bids = first_attr(msg, ["bids"], []) or []
    asks = first_attr(msg, ["asks"], []) or []

    bid_qty = sum(int(first_attr(level, ["quantity"], 0) or 0) for level in bids[:BOOK_LEVELS])
    ask_qty = sum(int(first_attr(level, ["quantity"], 0) or 0) for level in asks[:BOOK_LEVELS])
    book_imbalance = (bid_qty - ask_qty) / max(bid_qty + ask_qty, 1)

    momentum = 0.0
    if state.last_price and ltp:
        momentum = max(-1.0, min(1.0, (ltp - state.last_price) / state.last_price * MOMENTUM_GAIN))

    volume_impulse = 0.0
    if state.last_volume is not None and volume >= state.last_volume:
        volume_delta = volume - state.last_volume
        state.volume_deltas.append(volume_delta)
        avg_delta = sum(state.volume_deltas) / max(len(state.volume_deltas), 1)
        volume_impulse = min(1.0, volume_delta / max(avg_delta * 3.0, 1.0))

    if ltp:
        state.base_price = state.base_price or ltp
        state.price_points.append((time.time(), (ltp / state.base_price - 1.0) * 100.0))
    state.last_price = ltp or state.last_price
    state.last_volume = volume or state.last_volume

    # The volume impulse takes the sign of the momentum (or of the book if price is flat).
    sign_source = momentum or book_imbalance
    return (
        BOOK_WEIGHT * book_imbalance
        + MOMENTUM_WEIGHT * momentum
        + VOLUME_WEIGHT * math.copysign(volume_impulse, sign_source)
    )


def update_index_state(msg: Any, state: IndexState) -> bool:
    price = rupees(first_attr(msg, ["index_value", "last_traded_price", "ltp", "close"], 0))
    if not price:
        return False
    state.base_price = state.base_price or price
    state.last_price = price
    state.points.append((time.time(), (price / state.base_price - 1.0) * 100.0))
    return True


def pressure_score(states: dict[int, StockState]) -> float:
    """Weight-averaged mean per-stock pressure across NIFTY constituents, clipped to [-1, 1]."""
    live = [s for s in states.values() if s.pressure]
    total_weight = sum(s.weight for s in live)
    if total_weight <= 0:
        return 0.0
    raw = sum(s.weight * (sum(s.pressure) / len(s.pressure)) for s in live)
    return max(-1.0, min(1.0, raw / total_weight))


def top_pressure(states: dict[int, StockState], count: int = 6) -> list[tuple[str, float, float]]:
    """(symbol, weight, mean pressure) rows ranked by |weight * pressure|."""
    rows = [
        (s.symbol, s.weight, sum(s.pressure) / len(s.pressure))
        for s in states.values()
        if s.pressure
    ]
    return sorted(rows, key=lambda row: abs(row[1] * row[2]), reverse=True)[:count]


def recent_slope(points, lookback: int = 8) -> float:
    if len(points) < 2:
        return 0.0
    recent = list(points)[-lookback:]
    return recent[-1][1] - recent[0][1]


def relative_volume_100(state: StockState) -> float:
    """Latest volume delta as a percentage of its rolling average (100 = average), clipped to 10..300."""
    if not state.volume_deltas:
        return 100.0
    latest = state.volume_deltas[-1]
    avg = sum(state.volume_deltas) / max(len(state.volume_deltas), 1)
    return max(10.0, min(300.0, latest / max(avg, 1.0) * 100.0))


def participation_map(states: dict[int, StockState], index_state: IndexState) -> dict[str, Any]:
    """Volume-adjusted % change per stock against the NIFTY line, for the web chart."""
    series: list[dict[str, Any]] = []
    nifty_points = [[round(ts, 1), round(chg, 4)] for ts, chg in list(index_state.points)[-90:]]
    nifty_slope = recent_slope(index_state.points)
    nifty_dir = 1 if nifty_slope > 0 else -1 if nifty_slope < 0 else 0
    for state in states.values():
        if not state.price_points:
            continue
        pressure = sum(state.pressure) / len(state.pressure) if state.pressure else 0.0
        vol100 = relative_volume_100(state)
        multiplier = max(0.35, min(2.4, vol100 / 100.0))
        raw_points = list(state.price_points)[-90:]
        adjusted = [[round(ts, 1), round(chg * multiplier, 4)] for ts, chg in raw_points]
        stock_slope = recent_slope(raw_points)
        stock_dir = 1 if stock_slope > 0 else -1 if stock_slope < 0 else 0
        aligned = bool(nifty_dir and stock_dir and nifty_dir == stock_dir)
        diverging = bool(nifty_dir and stock_dir and nifty_dir != stock_dir)
        alignment = 1.0 if aligned else 0.35 if diverging else 0.15
        series.append({
            "symbol": state.symbol,
            "weight": round(state.weight, 2),
            "pressure": round(pressure, 4),
            "last": round(state.last_price or 0.0, 2),
            "change_pct": round(raw_points[-1][1], 4),
            "volume_100": round(vol100, 1),
            "adjusted_change": round(adjusted[-1][1], 4),
            "impact": round(state.weight * adjusted[-1][1] * alignment, 4),
            "aligned": aligned,
            "diverging": diverging,
            "direction": stock_dir,
            "points": adjusted,
        })
    series.sort(key=lambda item: abs(item["impact"]), reverse=True)
    aligned_weight = sum(i["weight"] for i in series if i["aligned"])
    confirmed_weight = sum(i["weight"] for i in series if i["aligned"] and i["volume_100"] >= 100)
    total_weight = sum(i["weight"] for i in series)
    return {
        "nifty": {
            "symbol": index_state.symbol,
            "last": round(index_state.last_price or 0.0, 2),
            "change_pct": None if not nifty_points else round(nifty_points[-1][1], 4),
            "direction": nifty_dir,
            "points": nifty_points,
        },
        "series": series,
        "leaders": sorted(series, key=lambda i: i["impact"], reverse=True)[:4],
        "laggards": sorted(series, key=lambda i: i["impact"])[:4],
        "aligned_weight": round(aligned_weight, 2),
        "confirmed_weight": round(confirmed_weight, 2),
        "participation": round(aligned_weight / max(total_weight, 1.0) * 100.0, 1),
    }
