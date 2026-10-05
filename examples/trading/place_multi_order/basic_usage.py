"""Place two independent limit orders (BUY ICICIBANK, SELL RELIANCE) in one request.
Type: mutating (UAT)
Needs: UAT login via env creds; market open for a live LTP
Expect: LTPs and order summaries in rupees; test order(s) are cancelled at the end if still open.
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


result = trader.create_order([
    {
        "refId": icici.ref_id,
        "qty": 1,
        "side": "BUY",
        "deliveryType": "IDAY",
        "priceType": "LIMIT",
        "validityType": "DAY",
        "isMultiLeg": False,
        "executionMode": "ENTRY",
        "entryPrice": to_tick(icici_ltp, icici.tick_size),
        "stratTags": ["python-sdk-v3-multi-limit-icici"],  # One tag only, hyphens only.
    },
    {
        "refId": reliance.ref_id,
        "qty": 1,
        "side": "SELL",
        "deliveryType": "IDAY",
        "priceType": "LIMIT",
        "validityType": "DAY",
        "isMultiLeg": False,
        "executionMode": "ENTRY",
        "entryPrice": to_tick(reliance_ltp, reliance.tick_size),
        "stratTags": ["python-sdk-v3-multi-limit-reliance"],  # One tag only, hyphens only.
    },
])

for o in result.orders:
    price = f"Rs {o.entryPrice / 100:.2f}" if o.entryPrice else "market"
    print(f"Order {o.intentOrderId}: {o.status or 'SUBMITTED'}, qty={o.orderQty}, price={price}")
    if o.rejectionMsg:
        print("  Rejected:", o.rejectionMsg)

# Clean up: cancel the test order(s) if still working.
time.sleep(2)  # orders reach the book ~1-2s after create
ids = [o.intentOrderId for o in result.orders]
live = [o for o in trader.get_order(ids) or [] if o.status not in ("EXECUTED", "REJECTED", "CANCELLED", "EXPIRED")]
if live:
    for attempt in range(3):
        try:
            print("Cancel:", trader.cancel_orders_sentinel([{"orderId": o.intentOrderId} for o in live]))
            break
        except Exception as err:  # the exchange may still be processing the order
            print(f"Cancel not accepted yet ({err}); retrying in 3s")
            time.sleep(3)
