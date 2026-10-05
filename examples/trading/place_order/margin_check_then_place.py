"""Check the margin for an order, and place it only if your available funds cover it.
Type: mutating (UAT)
Needs: UAT login via env creds; market open for a live LTP
Expect: LTP, funds required and available funds in rupees, then the order summary; the test order is cancelled at the end.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.portfolio.portfolio_data import NubraPortfolio
from nubra_python_sdk.trading.trading_data import NubraTrader
from nubra_python_sdk.trading.trading_enum import ExchangeEnum

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)
market_data = MarketData(nubra)
portfolio = NubraPortfolio(nubra)
trader = NubraTrader(nubra)

instrument = instruments.get_instrument_by_symbol("ICICIBANK", exchange=ExchangeEnum.NSE)
if isinstance(instrument, dict):
    raise SystemExit(instrument["msg"])  # symbol not found
tick_size = instrument.tick_size  # paise


def to_tick(price):
    return int(round(price / tick_size) * tick_size)


ltp = market_data.quote(ref_id=instrument.ref_id, levels=1).orderBook.last_traded_price  # paise
print(f"LTP: Rs {ltp / 100:.2f}")

# One order dict is used for both the margin check and the placement (prices in paise).
order = {
    "refId": instrument.ref_id,
    "qty": 1,
    "side": "BUY",
    "deliveryType": "IDAY",
    "priceType": "LIMIT",
    "validityType": "DAY",
    "isMultiLeg": False,
    "executionMode": "ENTRY",
    "entryPrice": to_tick(ltp * 0.98),  # resting limit below market
    "stratTags": ["python-sdk-v3-margin-guard"],  # One tag only, hyphens only.
}

funds = trader.get_margin({"requestType": "NEW", "orders": [order]})
required = funds.totalFundsRequired or 0  # paise
available = portfolio.funds().portFundsAndMargin.netMarginAvailable or 0  # paise
print(f"Funds required: Rs {required / 100:,.2f} | available: Rs {available / 100:,.2f}")

if required > available:
    print(f"Not placing: short by Rs {(required - available) / 100:,.2f}")
    raise SystemExit(0)  # expected outcome when funds are insufficient, not an error

result = trader.create_order(order)
for o in result.orders:
    print(f"Placed order {o.intentOrderId}: {o.status or 'SUBMITTED'}, price=Rs {(o.entryPrice or 0) / 100:.2f}")
    if o.rejectionMsg:
        print("  Rejected:", o.rejectionMsg)

# Clean up: cancel the test order if still working.
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
