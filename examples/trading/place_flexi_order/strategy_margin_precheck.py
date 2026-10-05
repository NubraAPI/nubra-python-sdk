"""Check margin for a NIFTY long straddle, and place the strategy order only if funds suffice.
Type: mutating (UAT)
Needs: UAT login via env creds; market open for NIFTY option LTPs
Expect: net premium, funds required and available funds in rupees, then the order summary; the test order is cancelled at the end.
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

chain = market_data.option_chain("NIFTY", exchange=ExchangeEnum.NSE).chain
calls = {o.strike_price: o for o in chain.ce}
puts = {o.strike_price: o for o in chain.pe}
strikes = sorted(set(calls) & set(puts))
atm = strikes.index(min(strikes, key=lambda s: abs(s - chain.at_the_money_strike)))
lot_size = calls[strikes[atm]].lot_size
tick_size = instruments.get_instrument_by_ref_id(calls[strikes[atm]].ref_id).tick_size  # paise


def to_tick(price):
    return int(round(price / tick_size) * tick_size)


def net_price(legs):
    # Strategy entryPrice is the signed net premium in paise (negative for a net credit).
    return to_tick(sum(qty * opt.last_traded_price for opt, qty in legs))


def leg_payload(legs):
    return [{"refId": opt.ref_id, "unitQty": qty} for opt, qty in legs]


legs = [(calls[strikes[atm]], 1), (puts[strikes[atm]], 1)]
net = net_price(legs)
print(f"Straddle net premium: Rs {net / 100:,.2f} per unit, lot size {lot_size}")

# One order dict is used for both the margin check and the placement (prices in paise).
order = {
    "isMultiLeg": True,
    "qty": lot_size,
    "side": "BUY",  # strategy side is always BUY; leg direction comes from the sign of unitQty
    "deliveryType": "CNC",
    "priceType": "LIMIT",
    "validityType": "DAY",
    "executionMode": "ENTRY",
    "entryPrice": to_tick(net * 0.9),  # resting limit below the net premium
    "legs": leg_payload(legs),
    "stratTags": ["python-sdk-v3-straddle-margin-guard"],  # One tag only, hyphens only.
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
    print(f"Placed strategy order {o.intentOrderId}: {o.status or 'SUBMITTED'}")
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
