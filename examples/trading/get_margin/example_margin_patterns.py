"""Check the margin needed for a 1-share ICICIBANK market order.
Type: read-only
Needs: UAT login via env creds
Expect: funds required and total margin in rupees. No order is placed.
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

# Market order margin: MARKET with IOC and no entryPrice, same as placement.

funds = trader.get_margin({
    "requestType": "NEW",
    "orders": [
        {
            "refId": instrument.ref_id,
            "qty": 1,
            "side": "BUY",
            "deliveryType": "IDAY",
            "priceType": "MARKET",
            "validityType": "IOC",
            "isMultiLeg": False,
            "executionMode": "ENTRY",
            "stratTags": ["python-sdk-v3-margin-market"],  # One tag only, hyphens only.
        },
    ],
})

print(f"Funds required: Rs {(funds.totalFundsRequired or 0) / 100:,.2f}")
print(f"Total margin:   Rs {(funds.marginInfo.totalMargin or 0) / 100:,.2f}")
if funds.marginInfo.message:
    print("Note:", funds.marginInfo.message)
