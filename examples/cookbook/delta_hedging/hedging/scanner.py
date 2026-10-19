"""Liquidity scan of F&O underlyings for the long future + short ATM call structure.

Read-only. For each underlying with a live future it looks at the things this
structure needs to fill cleanly: average daily future volume and OI trend
(``MarketData.historical_data``), the ATM call's volume and bid-ask spread
(``MarketData.option_chain`` and ``quote``). It ranks by a hand-picked liquidity
score. The score is a descriptive sort order only; it says nothing about
direction, value or expected returns, and is not a recommendation.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Sequence

import pandas as pd

from . import logic

HISTORICAL_RATE_LIMIT_PER_MIN = 60
"""Documented limit for historical data; the scan spaces those calls out."""

FUTURE_VOLUME_WEIGHT = 1.0
CALL_VOLUME_WEIGHT = 0.5
OI_TREND_WEIGHT = 0.2
SPREAD_PENALTY_WEIGHT = 5.0
MAX_SPREAD_PCT = 1.5
OI_TREND_CLAMP_PCT = 50.0
_ISO_Z = "%Y-%m-%dT%H:%M:%S.000Z"


@dataclass
class LiquidityScore:
    symbol: str
    exchange: str
    future_ref_id: Optional[int]
    lot_size: Optional[int]
    expiry: Optional[str]
    avg_daily_future_volume: Optional[float]
    fut_oi_trend_pct: Optional[float]
    atm_call_ref_id: Optional[int]
    atm_strike: Optional[float]  # rupees
    atm_delta: Optional[float]
    atm_iv: Optional[float]
    atm_call_volume: Optional[int]
    spread_pct: Optional[float]
    score: float
    liquid_enough: bool
    notes: str


class RateLimiter:
    """Fixed-interval throttle: spaces consecutive calls ``60 / max_per_minute`` seconds apart."""

    def __init__(self, max_per_minute: int = HISTORICAL_RATE_LIMIT_PER_MIN) -> None:
        self._gap = 60.0 / max_per_minute
        self._last: Optional[float] = None

    def wait(self) -> None:
        if self._last is not None:
            remaining = self._gap - (time.monotonic() - self._last)
            if remaining > 0:
                time.sleep(remaining)
        self._last = time.monotonic()


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def nearest_futures(instruments, exchange: str) -> pd.DataFrame:
    """One row per underlying: its nearest live future (expiry on/after today)."""
    df = instruments.get_instruments_dataframe(exchange=exchange)
    df = df[df["derivative_type"] == "FUT"].copy()
    df["expiry"] = pd.to_numeric(df["expiry"], errors="coerce")
    df = df[df["expiry"] >= int(date.today().strftime("%Y%m%d"))]
    return df.sort_values(["asset", "expiry"]).drop_duplicates("asset", keep="first")


def _points(chart, field_name: str) -> List[float]:
    pts = sorted(getattr(chart, field_name, None) or [], key=lambda p: p.timestamp or 0)
    return [float(p.value) for p in pts if p.value is not None]


def _future_series(market_data, exchange: str, contract: str, lookback_days: int):
    end = datetime.now(timezone.utc)
    response = market_data.historical_data(
        {
            "exchange": exchange,
            "type": "FUT",
            "values": [contract],
            "fields": ["cumulative_volume", "cumulative_fut_oi"],
            "startDate": (end - timedelta(days=lookback_days)).strftime(_ISO_Z),
            "endDate": end.strftime(_ISO_Z),
            "interval": "1d",
            "intraDay": False,
            "realTime": False,
        }
    )
    if response is None or not hasattr(response, "result") or not response.result:
        return None
    for entry in response.result[0].values or []:
        if contract in entry:
            return entry[contract]
    return None


def evaluate(market_data, row, exchange: str, lookback_days: int, limiter: Optional[RateLimiter]) -> LiquidityScore:
    """Score one underlying (``row`` is its nearest-future row from ``nearest_futures``)."""
    symbol, notes = str(row["asset"]), []
    expiry = str(int(row["expiry"]))
    base = dict(symbol=symbol, exchange=exchange, future_ref_id=int(row["ref_id"]),
                lot_size=int(row["lot_size"]), expiry=expiry)

    if limiter is not None:
        limiter.wait()
    try:
        series = _future_series(market_data, exchange, str(row["stock_name"]), lookback_days)
    except Exception as err:
        series = None
        notes.append(f"historical fetch failed ({err})")

    volumes = _points(series, "cumulative_volume") if series else []
    oi = _points(series, "cumulative_fut_oi") if series else []
    avg_volume = sum(volumes) / len(volumes) if volumes else None
    if avg_volume is None:
        notes.append("no recent future volume data")
    oi_trend = None
    if len(oi) >= 2 and oi[0]:
        oi_trend = (oi[-1] - oi[0]) / oi[0] * 100.0
        if oi_trend < -20.0:
            notes.append("declining future OI")
    elif not oi:
        notes.append("no future OI history")

    empty = dict(atm_call_ref_id=None, atm_strike=None, atm_delta=None, atm_iv=None,
                 atm_call_volume=None, spread_pct=None, score=0.0, liquid_enough=False)
    try:
        result = market_data.option_chain(symbol, expiry=expiry, exchange=exchange)
    except Exception as err:
        return LiquidityScore(**base, avg_daily_future_volume=avg_volume, fut_oi_trend_pct=oi_trend,
                              **empty, notes="; ".join(notes + [f"option chain failed ({err})"]))
    if result is None or not result.chain.ce:
        return LiquidityScore(**base, avg_daily_future_volume=avg_volume, fut_oi_trend_pct=oi_trend,
                              **empty, notes="; ".join(notes + ["no option chain data"]))

    chain = result.chain
    strikes = [c.strike_price / 100.0 for c in chain.ce]
    spot = chain.current_price / 100.0 if chain.current_price else None
    atm = chain.ce[logic.select_atm_call_index(strikes, [c.delta for c in chain.ce], spot)]

    if atm.iv is not None:
        if atm.iv < 10.0:
            notes.append("low IV: little premium in the short calls")
        elif atm.iv > 60.0:
            notes.append("high IV: wider option prices")

    spread_pct = None
    try:
        quote = market_data.quote(ref_id=atm.ref_id, levels=1)
        book = quote.orderBook if quote else None
        if book and book.bid and book.ask:
            bid, ask = book.bid[0].price, book.ask[0].price
            mid = (bid + ask) / 2.0
            if mid > 0:
                spread_pct = (ask - bid) / mid * 100.0
        if spread_pct is None:
            notes.append("no live quotes for ATM call")
    except Exception as err:
        notes.append(f"quote failed ({err})")
    if spread_pct is not None and spread_pct > MAX_SPREAD_PCT:
        notes.append(f"wide spread ({spread_pct:.2f}%)")
    if not atm.volume:
        notes.append("low or no recent ATM call volume")

    # score = w1*log1p(avg future volume) + w2*log1p(ATM call volume)
    #       + w3*clamp(OI trend %) - w4*spread %   (missing inputs add 0)
    score = (
        FUTURE_VOLUME_WEIGHT * math.log1p(avg_volume or 0.0)
        + CALL_VOLUME_WEIGHT * math.log1p(atm.volume or 0)
        + OI_TREND_WEIGHT * _clamp(oi_trend or 0.0, -OI_TREND_CLAMP_PCT, OI_TREND_CLAMP_PCT)
        - SPREAD_PENALTY_WEIGHT * (spread_pct if spread_pct is not None else MAX_SPREAD_PCT * 2)
    )
    liquid = bool(spread_pct is not None and spread_pct <= MAX_SPREAD_PCT and avg_volume and atm.volume)
    return LiquidityScore(
        **base,
        avg_daily_future_volume=avg_volume,
        fut_oi_trend_pct=oi_trend,
        atm_call_ref_id=atm.ref_id,
        atm_strike=strikes[chain.ce.index(atm)],
        atm_delta=atm.delta,
        atm_iv=atm.iv,
        atm_call_volume=atm.volume,
        spread_pct=spread_pct,
        score=score,
        liquid_enough=liquid,
        notes="; ".join(notes) if notes else "ok",
    )


def scan(instruments, market_data, exchange: str = "NSE", top_n: int = 15, lookback_days: int = 10,
         max_underlyings: Optional[int] = None) -> List[LiquidityScore]:
    """Score the F&O universe and return the ``top_n`` by liquidity score."""
    futures = nearest_futures(instruments, exchange)
    if max_underlyings is not None:
        futures = futures.head(max_underlyings)
    limiter = RateLimiter()
    scores: List[LiquidityScore] = []
    for _, row in futures.iterrows():
        try:
            scores.append(evaluate(market_data, row, exchange, lookback_days, limiter))
        except Exception as err:
            print(f"Skipping {row['asset']}: {err}")
    scores.sort(key=lambda s: s.score, reverse=True)
    return scores[:top_n]


def format_table(scores: Sequence[LiquidityScore]) -> str:
    def fmt(value, spec):
        return format(value, spec) if value is not None else "n/a"

    header = f"{'SYMBOL':<15}{'SCORE':>8}{'DELTA':>8}{'IV':>8}{'SPREAD%':>10}{'LIQUID':>8}  NOTES"
    lines = [header, "-" * len(header)]
    for s in scores:
        lines.append(
            f"{s.symbol:<15}{fmt(s.score, '8.2f')}{fmt(s.atm_delta, '8.3f')}{fmt(s.atm_iv, '8.2f')}"
            f"{fmt(s.spread_pct, '10.2f')}{str(s.liquid_enough):>8}  {s.notes}"
        )
    return "\n".join(lines)
