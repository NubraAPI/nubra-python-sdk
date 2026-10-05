"""Place a resting order, then poll get_order and print every status change until it settles.
Type: mutating (UAT)
Needs: UAT login via env creds; market open for a live LTP
Expect: status transitions such as OPEN -> CANCELLED with times; the order is cancelled mid-way, total run under 40s.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.trading.trading_data import NubraTrader
from nubra_python_sdk.trading.trading_enum import ExchangeEnum

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)
market_data = MarketData(nubra)
trader = NubraTrader(nubra)

TERMINAL = ("EXECUTED", "REJECTED", "CANCELLED", "EXPIRED")

instrument = instruments.get_instrument_by_symbol("ICICIBANK", exchange=ExchangeEnum.NSE)
if isinstance(instrument, dict):
    raise SystemExit(instrument["msg"])  # symbol not found
tick_size = instrument.tick_size  # paise


def to_tick(price):
    return int(round(price / tick_size) * tick_size)


def track(order_id, timeout, seen):
    """Poll get_order every second; print only when the status changes. Returns the list of statuses seen."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        orders = trader.get_order(order_id) or []  # a new order may take ~1-2s to appear
        if orders and (not seen or orders[0].status != seen[-1]):
            seen.append(orders[0].status)
            print(f"[{time.strftime('%H:%M:%S')}] order {order_id}: {orders[0].status}, "
                  f"filled {orders[0].filledQty}/{orders[0].orderQty}")
            if orders[0].rejectionMsg:
                print("  Rejected:", orders[0].rejectionMsg)
        if seen and seen[-1] in TERMINAL:
            break
        time.sleep(1)
    return seen


ltp = market_data.quote(ref_id=instrument.ref_id, levels=1).orderBook.last_traded_price  # paise
print(f"LTP: Rs {ltp / 100:.2f}")

entry = to_tick(ltp * 0.98)  # resting buy below market
placed = trader.create_order({
    "refId": instrument.ref_id,
    "qty": 1,
    "side": "BUY",
    "deliveryType": "IDAY",
    "priceType": "LIMIT",
    "validityType": "DAY",
    "isMultiLeg": False,
    "executionMode": "ENTRY",
    "entryPrice": entry,
    "stratTags": ["python-sdk-v3-track-status"],  # One tag only, hyphens only.
})
order_id = placed.orders[0].intentOrderId
print(f"Placed order {order_id} at Rs {entry / 100:.2f}")

seen = track(order_id, 6, [])  # watch it arrive in the book
if seen and seen[-1] not in TERMINAL:
    print("Cancel:", trader.cancel_orders_sentinel([{"orderId": order_id}]))
    seen = track(order_id, 15, seen)  # watch it settle
print("Status path:", " -> ".join(seen) or "order never appeared in the book")
