"""Modify two resting orders (ICICIBANK, RELIANCE) in one request, then cancel both.
Type: mutating (UAT)
Needs: UAT login via env creds; market open for a live LTP
Expect: LTP in rupees, acknowledgements and the order state after the modify; waits 5s before the final cancel.
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

icici = instruments.get_instrument_by_symbol("ICICIBANK", exchange=ExchangeEnum.NSE)
if isinstance(icici, dict):
    raise SystemExit(icici["msg"])  # symbol not found
reliance = instruments.get_instrument_by_symbol("RELIANCE", exchange=ExchangeEnum.NSE)
if isinstance(reliance, dict):
    raise SystemExit(reliance["msg"])  # symbol not found
icici_ltp = market_data.quote(ref_id=icici.ref_id, levels=1).orderBook.last_traded_price  # paise
print(f"ICICIBANK LTP: Rs {icici_ltp / 100:.2f}")
reliance_ltp = market_data.quote(ref_id=reliance.ref_id, levels=1).orderBook.last_traded_price  # paise
print(f"RELIANCE LTP: Rs {reliance_ltp / 100:.2f}")


def to_tick(price, tick_size):
    return int(round(price / tick_size) * tick_size)


placed = trader.create_order([
    {
        "refId": icici.ref_id,
        "qty": 1,
        "side": "BUY",
        "deliveryType": "IDAY",
        "priceType": "LIMIT",
        "validityType": "DAY",
        "isMultiLeg": False,
        "executionMode": "ENTRY",
        "entryPrice": to_tick(icici_ltp * 0.98, icici.tick_size),
        "stratTags": ["python-sdk-v3-modify-multi-icici"],  # One tag only, hyphens only.
    },
    {
        "refId": reliance.ref_id,
        "qty": 1,
        "side": "BUY",
        "deliveryType": "IDAY",
        "priceType": "LIMIT",
        "validityType": "DAY",
        "isMultiLeg": False,
        "executionMode": "ENTRY",
        "entryPrice": to_tick(reliance_ltp * 0.98, reliance.tick_size),
        "stratTags": ["python-sdk-v3-modify-multi-reliance"],  # One tag only, hyphens only.
    },
])
order_ids = [o.intentOrderId for o in placed.orders]
time.sleep(2)

# Modify several orders in one request: one item per orderId.
result = trader.modify_orders_sentinel([
    {
        "orderId": order_ids[0],
        "entryPrice": to_tick(icici_ltp * 0.97, icici.tick_size),
        "executionMode": "ENTRY",
    },
    {
        "orderId": order_ids[1],
        "entryPrice": to_tick(reliance_ltp * 0.97, reliance.tick_size),
        "executionMode": "ENTRY",
    },
])
print(result)
for o in trader.get_order(order_ids) or []:
    print(f"Order {o.intentOrderId}: {o.status}, qty={o.orderQty}, price=Rs {(o.entryPrice or 0) / 100:.2f}")
    if o.rejectionMsg:
        print("  Rejected:", o.rejectionMsg)

time.sleep(5)  # let the modify settle; an order cannot be cancelled while the exchange is processing a modify
# Clean up the test orders.
print(trader.cancel_orders_sentinel([{"orderId": oid} for oid in order_ids]))
