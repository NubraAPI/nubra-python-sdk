"""Black-Scholes delta/gamma fallback.

Nubra's option_chain() snapshot returns `delta` and `gamma` directly for each
strike, and the hedger uses those as the primary source (see
`nubra_client.NubraClient.get_market_tick`). This module is only used for a leg
whose `delta`/`gamma` come back as None.

SENSEX index options are European-style, so plain Black-Scholes applies with no
early-exercise adjustment.

IV unit assumption: the `iv` field is not documented with an explicit unit.
`normalize_iv` treats any value above 1.5 as a percentage (13.5 -> 13.5%) and
anything at or below 1.5 as an already-decimal fraction (0.135). Compare the
fallback numbers with the API Greeks on a live reading before relying on them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def normalize_iv(iv_raw: float | None) -> float:
    if iv_raw is None:
        return 0.0
    return iv_raw / 100.0 if iv_raw > 1.5 else iv_raw


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


@dataclass(frozen=True)
class BsGreeks:
    delta: float
    gamma: float


def black_scholes_greeks(
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    iv_decimal: float,
    risk_free_rate: float,
    option_type: str,
) -> BsGreeks:
    """Delta and gamma for one European option leg.

    `option_type` is "CE" or "PE" (Nubra's option-chain convention). Returns
    delta=0, gamma=0 for degenerate inputs (non-positive spot, strike, vol or
    time) instead of raising, because this runs every tick.
    """
    if spot <= 0 or strike <= 0 or iv_decimal <= 0 or time_to_expiry_years <= 0:
        return BsGreeks(delta=0.0, gamma=0.0)

    sqrt_t = math.sqrt(time_to_expiry_years)
    d1 = (
        math.log(spot / strike) + (risk_free_rate + 0.5 * iv_decimal * iv_decimal) * time_to_expiry_years
    ) / (iv_decimal * sqrt_t)

    is_call = option_type.upper() == "CE"
    delta = _norm_cdf(d1) if is_call else _norm_cdf(d1) - 1.0
    gamma = _norm_pdf(d1) / (spot * iv_decimal * sqrt_t)

    return BsGreeks(delta=delta, gamma=gamma)
