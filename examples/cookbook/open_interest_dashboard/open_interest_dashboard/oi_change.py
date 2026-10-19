"""Option-chain parsing and the open-interest change score."""
from __future__ import annotations

from typing import Any

from .config import OI_CONTRACT_COUNT, OI_DELTA_CENTER
from .models import OptionContract, first_attr, rupees


def parse_option_chain(msg: Any) -> list[OptionContract]:
    """Flatten an SDK option-chain object (REST snapshot or websocket message) into contracts.

    Rows without a ref_id, price or lot size are skipped. Prices and strikes arrive as paise.
    """
    msg = first_attr(msg, ["chain"], msg)
    contracts: list[OptionContract] = []
    for side_name, option_type in (("ce", "CE"), ("pe", "PE")):
        for raw in first_attr(msg, [side_name], []) or []:
            ref_id = first_attr(raw, ["ref_id"])
            ltp = rupees(first_attr(raw, ["last_traded_price", "ltp"]))
            lot_size = int(first_attr(raw, ["lot_size"], 0) or 0)
            if not ref_id or not ltp or not lot_size:
                continue
            oi = int(first_attr(raw, ["open_interest", "oi"], 0) or 0)
            # UAT returns previous_open_interest as None. Treat missing as "no change known"
            # (change 0) rather than "all OI is new", which would skew the OI score.
            previous_raw = first_attr(raw, ["previous_open_interest", "prev_oi"], None)
            previous_oi = oi if previous_raw is None else int(previous_raw)
            contracts.append(OptionContract(
                ref_id=int(ref_id),
                option_type=option_type,
                strike=rupees(first_attr(raw, ["strike_price", "sp"])),
                ltp=ltp,
                lot_size=lot_size,
                delta=float(first_attr(raw, ["delta"], 0.0) or 0.0),
                gamma=float(first_attr(raw, ["gamma"], 0.0) or 0.0),
                theta=float(first_attr(raw, ["theta"], 0.0) or 0.0),
                volume=int(first_attr(raw, ["volume"], 0) or 0),
                oi=oi,
                previous_oi=previous_oi,
            ))
    return contracts


def oi_change_score(contracts: list[OptionContract]) -> float:
    """(new put OI - new call OI) / (their sum), over the contracts closest to 0.45 absolute delta.

    Positive means more OI was added on puts than on calls (a bullish reading), negative the
    reverse. Only increases in OI are counted. Result is in [-1, 1].
    """
    near = sorted(contracts, key=lambda c: abs(abs(c.delta) - OI_DELTA_CENTER))[:OI_CONTRACT_COUNT]
    call_add = sum(max(0, c.oi_change) for c in near if c.option_type == "CE")
    put_add = sum(max(0, c.oi_change) for c in near if c.option_type == "PE")
    denom = max(call_add + put_add, 1)
    return max(-1.0, min(1.0, (put_add - call_add) / denom))
