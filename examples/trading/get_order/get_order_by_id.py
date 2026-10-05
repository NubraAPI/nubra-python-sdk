"""Place a resting ICICIBANK limit order and fetch it back with get_order.
Type: mutating (UAT)
Needs: UAT login via env creds; market open for a live LTP
Expect: order status, price in rupees and any rejection reason, then the cancel acknowledgement.
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

instrument = instruments.get_instrument_by_symbol("ICICIBANK", exchange=ExchangeEnum.NSE)
if isinstance(instrument, dict):
    raise SystemExit(instrument["msg"])  # symbol not found
tick_size = instrument.tick_size  # paise


def to_tick(price):
    return int(round(price / tick_size) * tick_size)


ltp = market_data.quote(ref_id=instrument.ref_id, levels=1).orderBook.last_traded_price  # paise
print(f"LTP: Rs {ltp / 100:.2f}")

# Place a small resting order (priced below market) so there is something to act on.
placed = trader.create_order({
    "refId": instrument.ref_id,
    "qty": 1,
    "side": "BUY",
    "deliveryType": "IDAY",
    "priceType": "LIMIT",
    "validityType": "DAY",
    "isMultiLeg": False,
    "executionMode": "ENTRY",
    "entryPrice": to_tick(ltp * 0.98),
    "stratTags": ["python-sdk-v3-get-order"],  # One tag only, hyphens only.
})
order_id = placed.orders[0].intentOrderId
time.sleep(2)  # give the order a moment to reach the order book

# get_order accepts one intentOrderId or a list, and returns a list of orders.
orders = trader.get_order(order_id)
for order in orders:
    print(order.intentOrderId, order.status, order.entryPrice, order.rejectionMsg)

# Clean up the test order.
print(trader.cancel_orders_sentinel([{"orderId": order_id}]))
