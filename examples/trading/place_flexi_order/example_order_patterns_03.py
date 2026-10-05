"""Place a NIFTY iron-condor strategy order (short inner, long wings).
Type: mutating (UAT)
Needs: UAT login via env creds; market open for NIFTY option LTPs
Expect: net premium in rupees and order summary; test order(s) are cancelled at the end if still open.
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


# Iron condor: short inner strikes, long outer wings.

legs = [
    (puts[strikes[atm - 4]], 1),
    (puts[strikes[atm - 2]], -1),
    (calls[strikes[atm + 2]], -1),
    (calls[strikes[atm + 4]], 1),
]
entry_price = net_price(legs)

result = trader.create_order({
    "isMultiLeg": True,
    "qty": lot_size,  # one strategy unit
    "side": "BUY",  # strategy side is always BUY; leg direction comes from the sign of unitQty
    "deliveryType": "CNC",
    "priceType": "LIMIT",
    "validityType": "DAY",
    "executionMode": "ENTRY",
    "entryPrice": entry_price,
    "legs": leg_payload(legs),
    "stratTags": ["python-sdk-v3-nifty-iron-condor"],  # One tag only, hyphens only.
})

for o in result.orders:
    price = f"Rs {o.entryPrice / 100:.2f}" if o.entryPrice else "market"
    print(f"Order {o.intentOrderId}: {o.status or 'SUBMITTED'}, qty={o.orderQty}, net premium={price}")
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
