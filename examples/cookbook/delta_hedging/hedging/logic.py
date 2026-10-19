"""Pure decision and accounting functions for the long future + short ATM calls hedge.

Everything here is a plain function over plain Python types: no SDK imports, no
network or file I/O, no clock reads. The backtester, the paper (dry-run) runner
and the live runner all call these same functions, so the hedge and exit maths
cannot diverge between them. Prices are rupees (floats) inside this module.
"""
from __future__ import annotations

from typing import Optional, Sequence, Tuple

MIN_HEDGE_SHARES: int = 1
"""Minimum |net delta| (in shares) worth acting on.

Option deltas jitter tick to tick. Re-hedging on every wiggle below one share
would only add order churn, so anything under this dead-band is left alone.
"""


def lots_to_shares(lots: int, lot_size: int) -> int:
    return lots * lot_size


def compute_net_delta_shares(
    future_qty_shares: float,
    short_call_deltas: Sequence[float],
    short_call_qty_shares: Sequence[float],
    equity_hedge_shares: float,
) -> float:
    """Net position delta, in underlying shares.

    - The future contributes ``future_qty_shares`` at delta 1.0 per share.
    - Each short call leg contributes ``-delta * qty_shares`` (a quoted option
      delta describes a long position; being short flips the sign).
      ``short_call_deltas`` and ``short_call_qty_shares`` are parallel
      sequences with positive share counts.
    - ``equity_hedge_shares`` is the signed share count already held in the
      cash equity (positive = long, negative = short), delta 1.0 per share.
    """
    short_calls_delta = -sum(
        delta * qty for delta, qty in zip(short_call_deltas, short_call_qty_shares)
    )
    return future_qty_shares + short_calls_delta + equity_hedge_shares


def compute_hedge_order(
    net_delta_shares: float, min_shares: int = MIN_HEDGE_SHARES
) -> Optional[Tuple[str, int]]:
    """Equity order that would flatten ``net_delta_shares``, or ``None``.

    Positive net delta (net long the underlying) -> SELL equity. Negative net
    delta (net short) -> BUY equity. ``None`` inside the dead-band.
    """
    qty = round(abs(net_delta_shares))
    if qty < min_shares:
        return None
    side = "SELL" if net_delta_shares > 0 else "BUY"
    return side, int(qty)


def should_check_rehedge(
    last_hedge_price: float, current_price: float, hedge_trigger_pct: float
) -> bool:
    """True when the underlying has moved at least ``hedge_trigger_pct`` percent
    since the last hedge (or since entry, before any hedge).

    Net delta is recomputed only on a threshold crossing, not on every tick. An
    unset/zero reference price means "always check".
    """
    if last_hedge_price <= 0:
        return True
    pct_move = abs(current_price - last_hedge_price) / last_hedge_price * 100.0
    return pct_move >= hedge_trigger_pct


def evaluate_exit(
    total_pnl: float, pnl_target: float, pnl_stop_loss: float
) -> Tuple[bool, str]:
    """Whether the whole structure should be closed, purely on total PnL.

    ``pnl_stop_loss`` is zero or negative (for example -5000): exit once
    ``total_pnl <= pnl_stop_loss``. ``pnl_target`` is positive: exit once
    ``total_pnl >= pnl_target``. ``total_pnl`` must already net the future,
    the short calls and the equity hedge into one rupee figure.
    """
    if total_pnl >= pnl_target:
        return True, f"pnl_target_hit: total_pnl={total_pnl:.2f} >= pnl_target={pnl_target:.2f}"
    if total_pnl <= pnl_stop_loss:
        return True, f"stop_loss_hit: total_pnl={total_pnl:.2f} <= pnl_stop_loss={pnl_stop_loss:.2f}"
    return False, ""


def select_atm_call_index(
    strikes: Sequence[float],
    deltas: Optional[Sequence[Optional[float]]],
    underlying_price: Optional[float],
) -> int:
    """Index into ``strikes`` of the ATM call to short.

    Prefers the call whose live delta is closest to 0.5 when at least one delta
    is available (it reflects the market's own view of at-the-money-ness).
    Falls back to the strike numerically closest to ``underlying_price``.
    """
    if deltas is not None and any(d is not None for d in deltas):
        return min(
            range(len(deltas)),
            key=lambda i: abs((deltas[i] if deltas[i] is not None else 0.0) - 0.5),
        )
    if underlying_price is None:
        raise ValueError(
            "select_atm_call_index needs either usable deltas or an underlying_price"
        )
    return min(range(len(strikes)), key=lambda i: abs(strikes[i] - underlying_price))


def apply_hedge_fill(
    *,
    prev_shares: float,
    avg_hedge_price: float,
    realized_pnl: float,
    side: str,
    qty: int,
    fill_price: float,
) -> Tuple[float, float, float]:
    """Average-price and realised-PnL bookkeeping for one equity hedge fill.

    Returns ``(new_shares, new_avg_hedge_price, new_realized_pnl)``. Adding to
    the hedge blends the average price; reducing or flipping it realises PnL on
    the closed portion at the existing average price.
    """
    signed_qty = qty if side == "BUY" else -qty
    new_shares = prev_shares + signed_qty
    same_direction_or_opening = prev_shares == 0 or (prev_shares > 0) == (signed_qty > 0)
    if same_direction_or_opening:
        total_cost = avg_hedge_price * abs(prev_shares) + fill_price * qty
        new_avg = total_cost / abs(new_shares) if new_shares != 0 else 0.0
        return new_shares, new_avg, realized_pnl
    closing_qty = min(qty, abs(prev_shares))
    direction = 1 if prev_shares > 0 else -1
    new_realized = realized_pnl + direction * (fill_price - avg_hedge_price) * closing_qty
    if new_shares == 0:
        new_avg = 0.0
    elif (new_shares > 0) != (prev_shares > 0):
        new_avg = fill_price
    else:
        new_avg = avg_hedge_price
    return new_shares, new_avg, new_realized


def mark_to_market_pnl(
    *,
    entry_future_price: float,
    future_price: float,
    future_qty_shares: float,
    entry_call_price: float,
    call_price: float,
    short_call_qty_shares: float,
    equity_hedge_shares: float,
    equity_avg_hedge_price: float,
    equity_price: float,
    realized_hedge_pnl: float,
) -> float:
    """Total PnL in rupees of future + short calls + equity hedge.

    The future gains as price rises; the short calls gain as the option price
    falls (sign flipped); the equity hedge is marked at its average price.
    ``short_call_qty_shares`` is the total shares short across all call lots.
    """
    future_mtm = (future_price - entry_future_price) * future_qty_shares
    short_calls_mtm = (entry_call_price - call_price) * short_call_qty_shares
    equity_unrealized = (
        (equity_price - equity_avg_hedge_price) * equity_hedge_shares
        if equity_hedge_shares != 0
        else 0.0
    )
    return future_mtm + short_calls_mtm + realized_hedge_pnl + equity_unrealized


def max_drawdown(pnl_series: Sequence[float]) -> float:
    peak = float("-inf")
    worst = 0.0
    for value in pnl_series:
        peak = max(peak, value)
        worst = max(worst, peak - value)
    return worst
