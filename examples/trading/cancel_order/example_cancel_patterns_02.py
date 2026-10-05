"""Place two resting orders and cancel both in one request.
Type: mutating (UAT)
Needs: UAT login via env creds; market open for a live LTP
Expect: both LTPs in rupees and one cancel acknowledgement.
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
        "stratTags": ["python-sdk-v3-cancel-multi-icici"],  # One tag only, hyphens only.
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
        "stratTags": ["python-sdk-v3-cancel-multi-reliance"],  # One tag only, hyphens only.
    },
])
order_ids = [o.intentOrderId for o in placed.orders]
time.sleep(2)

# Cancel several orders in one request.
result = trader.cancel_orders_sentinel([{"orderId": oid} for oid in order_ids])
print(result)
