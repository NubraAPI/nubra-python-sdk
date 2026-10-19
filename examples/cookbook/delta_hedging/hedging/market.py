"""SDK lookups used by the hedge runner, scanner and dashboard.

Thin helpers over ``InstrumentData`` and ``MarketData``. Prices returned by the
SDK are integer paise; the helpers here convert to rupees where noted.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd

from . import logic


@dataclass(frozen=True)
class HedgeLegs:
    """Contracts and reference prices (rupees) resolved for one hedge."""

    symbol: str
    exchange: str
    future_ref_id: int
    future_symbol: str
    lot_size: int
    expiry: str  # YYYYMMDD
    call_ref_id: int
    call_strike: float
    call_ltp: float
    call_delta: Optional[float]
    underlying_price: Optional[float]
    equity_ref_id: Optional[int]


def nearest_future_row(instruments, symbol: str, exchange: str, expiry: Optional[str] = None):
    """Row (pandas Series) of the nearest live future for ``symbol``.

    ``expiry`` is an optional YYYY-MM-DD or YYYYMMDD string to pick a specific
    expiry instead of the nearest one on or after today.
    """
    df = instruments.get_instruments_dataframe(exchange=exchange)
    if df is None or df.empty:
        raise RuntimeError(f"No instrument master loaded for {exchange}")
    expiries = pd.to_numeric(df["expiry"], errors="coerce")
    fut = df[(df["asset"] == symbol) & (df["derivative_type"] == "FUT")].copy()
    fut["expiry"] = expiries.loc[fut.index]
    if fut.empty:
        raise RuntimeError(f"No FUT instrument found for asset {symbol!r} on {exchange}")
    if expiry:
        target = int(str(expiry).replace("-", ""))
        match = fut[fut["expiry"] == target]
        if match.empty:
            raise RuntimeError(f"No FUT instrument for {symbol!r} with expiry {expiry}")
        return match.iloc[0]
    today = int(date.today().strftime("%Y%m%d"))
    upcoming = fut[fut["expiry"] >= today]
    if upcoming.empty:
        raise RuntimeError(f"No live FUT expiry on/after today for {symbol!r}")
    return upcoming.sort_values("expiry").iloc[0]


def last_price(market_data, ref_id: int) -> Optional[float]:
    """Last traded price in rupees from a one-level quote, or None."""
    quote = market_data.quote(ref_id=ref_id, levels=1)
    if quote is None or quote.orderBook is None or not quote.orderBook.last_traded_price:
        return None
    return quote.orderBook.last_traded_price / 100.0


def resolve_legs(instruments, market_data, symbol: str, exchange: str,
                 expiry: Optional[str] = None) -> HedgeLegs:
    """Resolve the future, the ATM call to short and the cash equity for ``symbol``."""
    fut = nearest_future_row(instruments, symbol, exchange, expiry)
    expiry_str = str(int(fut["expiry"]))

    result = market_data.option_chain(symbol, expiry=expiry_str, exchange=exchange)
    if result is None or not result.chain.ce:
        raise RuntimeError(f"Option chain for {symbol} expiry {expiry_str} has no call legs")
    chain = result.chain
    calls = chain.ce
    strikes = [c.strike_price / 100.0 for c in calls]  # strike prices arrive in paise
    deltas = [c.delta for c in calls]
    underlying = chain.current_price / 100.0 if chain.current_price else None
    idx = logic.select_atm_call_index(strikes, deltas, underlying)
    atm_call = calls[idx]

    equity = instruments.get_instrument_by_symbol(symbol, exchange=exchange)
    equity_ref_id = None if isinstance(equity, dict) else equity.ref_id

    return HedgeLegs(
        symbol=symbol,
        exchange=exchange,
        future_ref_id=int(fut["ref_id"]),
        future_symbol=str(fut["stock_name"]),
        lot_size=int(fut["lot_size"]),
        expiry=expiry_str,
        call_ref_id=atm_call.ref_id,
        call_strike=strikes[idx],
        call_ltp=(atm_call.last_traded_price or 0) / 100.0,
        call_delta=atm_call.delta,
        underlying_price=underlying,
        equity_ref_id=equity_ref_id,
    )
