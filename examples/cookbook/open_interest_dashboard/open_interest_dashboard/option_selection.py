"""Rank option contracts on delta/gamma and affordability, and size one lot."""
from __future__ import annotations

from .config import AFFORDABLE_FRACTION, RANK_DELTA_CENTER, WATCH_COUNT
from .models import Direction, OptionContract


def is_affordable(contract: OptionContract, capital: float) -> bool:
    return contract.lot_cost <= capital * AFFORDABLE_FRACTION


def choose_contract(
    contracts: list[OptionContract], direction: Direction, capital: float
) -> OptionContract | None:
    """Best candidate on the matching side: CE for a bullish reading, PE for a bearish one.

    Filters: traded volume > 0, gamma > 0, one lot costs at most 95% of `capital`.
    Ranking: |delta| closest to 0.42, then higher gamma, volume and open interest.
    """
    option_type = "CE" if direction == Direction.BULLISH else "PE"
    eligible = [
        c for c in contracts
        if c.option_type == option_type and c.volume > 0 and c.gamma > 0 and is_affordable(c, capital)
    ]
    if not eligible:
        return None
    return max(
        eligible,
        key=lambda c: (-abs(abs(c.delta) - RANK_DELTA_CENTER), c.gamma, c.volume, c.oi),
    )


def ranked_contracts(contracts: list[OptionContract], capital: float) -> dict[str, list[dict]]:
    """Top contracts per side for the dashboard table (affordable ones first)."""
    result: dict[str, list[dict]] = {"CE": [], "PE": []}
    for side in result:
        side_rows = [c for c in contracts if c.option_type == side and c.ltp > 0 and c.lot_size > 0]
        ranked = sorted(
            side_rows,
            key=lambda c: (
                is_affordable(c, capital),
                -abs(abs(c.delta) - RANK_DELTA_CENTER),
                c.gamma,
                c.volume,
                abs(c.oi_change),
            ),
            reverse=True,
        )[:WATCH_COUNT]
        result[side] = [
            {
                "ref_id": c.ref_id,
                "strike": c.strike,
                "ltp": c.ltp,
                "delta": c.delta,
                "gamma": c.gamma,
                "volume": c.volume,
                "oi": c.oi,
                "oi_change": c.oi_change,
                "lot_cost": round(c.lot_cost, 2),
                "affordable": is_affordable(c, capital),
            }
            for c in ranked
        ]
    return result


def size_one_lot(
    contract: OptionContract, capital: float, risk_fraction: float, stoploss_pct: float
) -> int:
    """Units for one lot, or 0 if the lot is unaffordable or its reference loss exceeds the risk budget.

    Reference loss per unit = ltp * stoploss_pct / 100; budget = capital * risk_fraction.
    """
    risk_per_unit = max(contract.ltp * stoploss_pct / 100.0, 0.05)
    lots_by_risk = int((capital * risk_fraction) // (risk_per_unit * contract.lot_size))
    lots_by_capital = int((capital * AFFORDABLE_FRACTION) // contract.lot_cost)
    lots = max(0, min(lots_by_risk, lots_by_capital, 1))
    return lots * contract.lot_size
