"""Blend the pressure score and the OI score into one market reading."""
from __future__ import annotations

from .config import OI_BLEND, PRESSURE_BLEND
from .models import Direction, MarketReading, OptionContract, StockState
from .oi_change import oi_change_score
from .option_selection import choose_contract, size_one_lot
from .pressure import pressure_score


def build_reading(
    states: dict[int, StockState],
    contracts: list[OptionContract],
    capital: float,
    min_score: float,
    risk_fraction: float,
    min_pressure_abs: float,
    min_oi_abs: float,
    stoploss_pct: float,
) -> MarketReading:
    """Direction is NEUTRAL unless pressure and OI are each strong, agree in sign, and the
    blended score clears `min_score`. A directional reading also carries the best-ranked
    candidate contract (if one passes the filters)."""
    pressure = pressure_score(states)
    oi = oi_change_score(contracts)
    score = PRESSURE_BLEND * pressure + OI_BLEND * oi

    if abs(pressure) < min_pressure_abs or abs(oi) < min_oi_abs:
        return MarketReading(Direction.NEUTRAL, score, pressure, oi, "pressure or OI score below minimum")
    if pressure * oi <= 0:
        return MarketReading(Direction.NEUTRAL, score, pressure, oi, "pressure and OI disagree")
    if abs(score) < min_score:
        return MarketReading(Direction.NEUTRAL, score, pressure, oi, "bias score below threshold")

    direction = Direction.BULLISH if score > 0 else Direction.BEARISH
    contract = choose_contract(contracts, direction, capital)
    if not contract:
        return MarketReading(direction, score, pressure, oi, "no liquid affordable candidate contract")

    qty = size_one_lot(contract, capital, risk_fraction, stoploss_pct)
    if qty <= 0:
        return MarketReading(direction, score, pressure, oi, "candidate excluded by capital/risk filter", contract=contract)

    side = "CE" if direction == Direction.BULLISH else "PE"
    return MarketReading(
        direction, score, pressure, oi,
        f"pressure and OI agree; top-ranked {side} has positive gamma",
        contract=contract, qty=qty,
    )
