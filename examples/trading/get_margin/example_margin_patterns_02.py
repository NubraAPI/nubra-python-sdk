"""Check the margin needed for one lot of nearest-expiry HDFCBANK futures.
Type: read-only
Needs: UAT login via env creds; market open for a live LTP
Expect: futures LTP, funds required and total margin in rupees. No order is placed.
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

# Nearest-expiry HDFCBANK futures contract.
df = instruments.get_instruments_dataframe(exchange="NSE")
futures = df[(df["asset"] == "HDFCBANK") & (df["derivative_type"] == "FUT")].sort_values("expiry")
if futures.empty:
    raise ValueError("No active HDFCBANK futures contract found")

fut = futures.iloc[0]
fut_ref_id = int(fut["ref_id"])
fut_lot_size = int(fut["lot_size"])
fut_tick_size = int(fut["tick_size"])
fut_ltp = market_data.quote(ref_id=fut_ref_id, levels=1).orderBook.last_traded_price  # paise
print(f"Futures LTP: Rs {fut_ltp / 100:.2f}")

funds = trader.get_margin({
    "requestType": "NEW",
    "orders": [
        {
            "refId": fut_ref_id,
            "qty": fut_lot_size,
            "side": "BUY",
            "deliveryType": "IDAY",
            "priceType": "LIMIT",
            "validityType": "DAY",
            "isMultiLeg": False,
            "executionMode": "ENTRY",
            "entryPrice": int(round(fut_ltp / fut_tick_size) * fut_tick_size),
            "stratTags": ["python-sdk-v3-margin-futures"],  # One tag only, hyphens only.
        },
    ],
})

print(f"Funds required: Rs {(funds.totalFundsRequired or 0) / 100:,.2f}")
print(f"Total margin:   Rs {(funds.marginInfo.totalMargin or 0) / 100:,.2f}")
if funds.marginInfo.message:
    print("Note:", funds.marginInfo.message)
