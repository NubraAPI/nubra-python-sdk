"""Bracket-style equity trade: limit entry with a stop-loss and a profit target attached.
Type: mutating (UAT)
Needs: UAT login via env creds; market open for a live LTP
Expect: LTP, entry/stop-loss/target in rupees with risk vs reward, the order summary; the test order is cancelled at the end.
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

instrument = instruments.get_instrument_by_symbol("ICICIBANK", exchange=ExchangeEnum.NSE)
if isinstance(instrument, dict):
    raise SystemExit(instrument["msg"])  # symbol not found
tick_size = instrument.tick_size  # paise


def to_tick(price):
    return int(round(price / tick_size) * tick_size)


ltp = market_data.quote(ref_id=instrument.ref_id, levels=1).orderBook.last_traded_price  # paise
print(f"LTP: Rs {ltp / 100:.2f}")

entry = to_tick(ltp * 0.98)  # resting buy below market so it does not fill
sl_trigger, sl_limit = to_tick(entry * 0.99), to_tick(entry * 0.989)  # stop-loss limit <= trigger
tp_trigger, tp_limit = to_tick(entry * 1.02), to_tick(entry * 1.019)

# Sanity-check the bracket before sending it.
if not (sl_limit <= sl_trigger < entry < tp_trigger):
    raise SystemExit("Bracket levels are not ordered correctly for a BUY; adjust the percentages.")
risk, reward = entry - sl_trigger, tp_trigger - entry
print(f"Entry Rs {entry / 100:.2f} | stop-loss Rs {sl_trigger / 100:.2f} | target Rs {tp_trigger / 100:.2f}")
print(f"Risk Rs {risk / 100:.2f} vs reward Rs {reward / 100:.2f} per share (1:{reward / risk:.1f})")

result = trader.create_order({
    "refId": instrument.ref_id,
    "qty": 1,
    "side": "BUY",
    "deliveryType": "IDAY",
    "priceType": "LIMIT",
    "validityType": "DAY",
    "isMultiLeg": False,
    "executionMode": "ENTRY_AND_EXIT",
    "entryPrice": entry,
    "exitConfig": {
        "stoplossParams": {
            "stoplossTriggerPrice": {"value": sl_trigger},
            "stoplossLimitPrice": {"value": sl_limit},
        },
        "targetParams": {
            "targetProfitTriggerPrice": {"value": tp_trigger},
            "targetProfitLimitPrice": {"value": tp_limit},
        },
    },
    "stratTags": ["python-sdk-v3-bracket-entry"],  # One tag only, hyphens only.
})
for o in result.orders:
    print(f"Placed order {o.intentOrderId}: {o.status or 'SUBMITTED'}")
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
