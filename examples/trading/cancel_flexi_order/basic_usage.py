"""Place a resting NIFTY long-straddle strategy order, then cancel it by its strategy-level id.
Type: mutating (UAT)
Needs: UAT login via env creds; market open for NIFTY option LTPs
Expect: the cancel acknowledgement for the strategy order (placed priced below market so it rests).
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


# Place a small resting strategy order (priced below the net premium) so there is something to act on.
legs = [(calls[strikes[atm]], 1), (puts[strikes[atm]], 1)]
placed = trader.create_order({
    "isMultiLeg": True,
    "qty": lot_size,
    "side": "BUY",
    "deliveryType": "CNC",
    "priceType": "LIMIT",
    "validityType": "DAY",
    "executionMode": "ENTRY",
    "entryPrice": to_tick(net_price(legs) * 0.9),
    "legs": leg_payload(legs),
    "stratTags": ["python-sdk-v3-cancel-strategy"],  # One tag only, hyphens only.
})
strategy_order_id = placed.orders[0].intentOrderId  # one strategy-level id; legs have no ids
time.sleep(2)

# Cancel the whole strategy by its strategy-level intentOrderId.
result = trader.cancel_orders_sentinel([{"orderId": strategy_order_id}])
print(result)
