"""Optional order helper. Off by default: without --place-orders it only builds the payload."""
from __future__ import annotations

import re
from datetime import datetime, time as dtime
from typing import Any

from .models import MarketReading, paise

TAG_PATTERN = re.compile(r"^[A-Za-z0-9-]+$")  # the SDK accepts one tag, hyphens only


def check_order_flags(args: Any) -> str | None:
    """Return an error message if the order-related flags are unsafe or invalid, else None."""
    if not TAG_PATTERN.match(args.order_tag):
        return "--order-tag may only contain letters, digits and hyphens"
    if args.place_orders and args.env == "PROD" and not args.allow_prod:
        return "--place-orders on PROD also requires --allow-prod. Run on UAT first."
    return None


def market_is_open() -> bool:
    now = datetime.now().time()
    return dtime(9, 16) <= now <= dtime(15, 10)


def build_order_payload(reading: MarketReading, args: Any, tick_size: int = 5) -> dict[str, Any]:
    """Single-leg BUY payload for the candidate contract, in the SDK's create_order format.

    Prices are integer paise rounded to `tick_size`.
    - "entry":   limit entry only.
    - "bracket": limit entry plus stop-loss and target (executionMode ENTRY_AND_EXIT).
    The entry limit sits `--entry-limit-buffer-pct` above the contract LTP; stop-loss and target
    are measured from the contract LTP (`--stoploss-pct`, `--target-multiple` x the stop distance).
    """
    contract = reading.contract
    if contract is None or reading.qty <= 0:
        raise ValueError("No candidate contract with a valid quantity")

    def to_tick(value: float) -> int:
        return max(tick_size, int(round(value / tick_size) * tick_size))

    ltp = paise(contract.ltp)
    entry = to_tick(ltp * (1.0 + args.entry_limit_buffer_pct / 100.0))
    payload: dict[str, Any] = {
        "refId": contract.ref_id,
        "qty": reading.qty,
        "side": "BUY",
        "deliveryType": "IDAY",
        "priceType": "LIMIT",
        "validityType": "DAY",
        "isMultiLeg": False,
        "executionMode": "ENTRY",
        "entryPrice": entry,
        "stratTags": [args.order_tag],
    }
    if args.order_mode == "bracket":
        stop_distance = ltp * args.stoploss_pct / 100.0
        sl_trigger = to_tick(min(ltp - stop_distance, entry - tick_size))
        sl_limit = to_tick(sl_trigger * 0.99)  # limit <= trigger
        tp_trigger = to_tick(max(ltp + args.target_multiple * stop_distance, entry + tick_size))
        tp_limit = to_tick(tp_trigger - tick_size)
        if not (sl_limit <= sl_trigger < entry < tp_trigger):
            raise ValueError("Bracket levels are not ordered correctly; adjust the percentages")
        payload["executionMode"] = "ENTRY_AND_EXIT"
        payload["exitConfig"] = {
            "stoplossParams": {
                "stoplossTriggerPrice": {"value": sl_trigger},
                "stoplossLimitPrice": {"value": sl_limit},
            },
            "targetParams": {
                "targetProfitTriggerPrice": {"value": tp_trigger},
                "targetProfitLimitPrice": {"value": tp_limit},
            },
        }
    return payload


def describe_response(response: Any) -> str:
    orders = getattr(response, "orders", None)
    if not orders:
        return str(response)
    parts = []
    for o in orders:
        text = f"order {getattr(o, 'intentOrderId', '?')}: {getattr(o, 'status', None) or 'SUBMITTED'}"
        if getattr(o, "rejectionMsg", None):
            text += f" (rejected: {o.rejectionMsg})"
        parts.append(text)
    return "; ".join(parts)
