"""Place a NIFTY bull-call-spread GTE order with trigger entry, trailing stop-loss and target.
Type: mutating (UAT)
Needs: UAT login via env creds; market open for NIFTY option LTPs
Expect: net premium in rupees and order summary; test order(s) are cancelled at the end if still open.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time
from datetime import datetime, timedelta, timezone
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


# Bull call spread: GTE validity with trigger entry, trailing stop-loss and target.
# Do not send exitConfig.exitTime together with GTE. goodTillDate must not be after the option expiry.

legs = [(calls[strikes[atm]], 1), (calls[strikes[atm + 2]], -1)]
entry_price = net_price(legs)
# Keep goodTillDate within two days and never after the option expiry (expiry is YYYYMMDD).
expiry_day = datetime.strptime(str(chain.expiry), "%Y%m%d").replace(hour=9, tzinfo=timezone.utc)
good_till = min(datetime.now(timezone.utc) + timedelta(days=2), expiry_day).strftime("%Y-%m-%dT%H:%M:%S.000Z")

result = trader.create_order({
    "isMultiLeg": True,
    "qty": lot_size,  # one strategy unit
    "side": "BUY",  # strategy side is always BUY; leg direction comes from the sign of unitQty
    "deliveryType": "CNC",
    "priceType": "LIMIT",
    "validityType": "GTE",
    "executionMode": "ENTRY_AND_EXIT",
    "entryPrice": entry_price,
    "legs": leg_payload(legs),
    "goodTillDate": good_till,
    "entryConfig": {
        "triggers": {"ltp": {"atOrAbove": {"value": to_tick(entry_price * 1.02)}}},
    },
    "exitConfig": {
        "stoplossParams": {
            "stoplossTriggerPrice": {"value": to_tick(entry_price * 0.9)},
            "stoplossLimitPrice": {"value": to_tick(entry_price * 0.89)},
            "stoplossTrailJump": 5,
        },
        "targetParams": {
            "targetProfitTriggerPrice": {"value": to_tick(entry_price * 1.2)},
            "targetProfitLimitPrice": {"value": to_tick(entry_price * 1.19)},
        },
    },
    "stratTags": ["python-sdk-v3-nifty-bull-call-spread"],  # One tag only, hyphens only.
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
