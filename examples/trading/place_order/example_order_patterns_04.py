"""Place a 1-share ICICIBANK MARKET order (IOC, no price).
Type: mutating (UAT) - fills at once and opens a position
Needs: UAT login via env creds; market open
Expect: order id and status. It executes immediately, so nothing is cancelled; flatten with square_off_all_positions.py.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
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

# Market order: priceType MARKET with validityType IOC, and no entryPrice.

result = trader.create_order({
    "refId": instrument.ref_id,
    "qty": 1,
    "side": "BUY",
    "deliveryType": "IDAY",
    "priceType": "MARKET",
    "validityType": "IOC",
    "isMultiLeg": False,
    "executionMode": "ENTRY",
    "stratTags": ["python-sdk-v3-single-market"],  # One tag only, hyphens only.
})

for o in result.orders:
    price = f"Rs {o.entryPrice / 100:.2f}" if o.entryPrice else "market"
    print(f"Order {o.intentOrderId}: {o.status or 'SUBMITTED'}, qty={o.orderQty}, price={price}")
    if o.rejectionMsg:
        print("  Rejected:", o.rejectionMsg)
