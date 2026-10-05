"""Live order book depth imbalance for HDFCBANK: total bid quantity vs total ask quantity.

Type: streaming
Needs: UAT login (PHONE_NO / MPIN in .env); market hours for ticks.
Expect: about one line per second: best bid/ask (rupees), bid qty, ask qty, imbalance in -100..+100
        (positive = more buyers in the book); stops after 25 seconds, or "No data received - market closed?".
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time

from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.ticker import websocketdata
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

RUN_SECONDS = 25

instrument = InstrumentData(nubra).get_instrument_by_symbol("HDFCBANK", exchange="NSE")
if isinstance(instrument, dict):  # not found -> {"msg": "..."}
    raise SystemExit(f"Instrument lookup failed: {instrument.get('msg')}")
ref_id = str(instrument.ref_id)

def rupees(paise):
    return "-" if paise is None else f"{paise / 100:,.2f}"

state = {"n": 0, "last_print": 0.0}

def on_orderbook_data(msg):
    state["n"] += 1
    bids, asks = (getattr(msg, "bids", None) or []), (getattr(msg, "asks", None) or [])
    bid_qty = sum(getattr(b, "quantity", 0) or 0 for b in bids)
    ask_qty = sum(getattr(a, "quantity", 0) or 0 for a in asks)
    total = bid_qty + ask_qty
    if not total:
        return
    now = time.time()
    if now - state["last_print"] < 1:  # throttle to ~1 line per second
        return
    state["last_print"] = now
    imbalance = 100 * (bid_qty - ask_qty) / total
    best_bid = getattr(bids[0], "price", None) if bids else None
    best_ask = getattr(asks[0], "price", None) if asks else None
    print(f"bid {rupees(best_bid)} | ask {rupees(best_ask)} | "
          f"bid qty {bid_qty} | ask qty {ask_qty} | imbalance {imbalance:+.0f}")

def on_connect(msg):
    print("[status]", msg)

def on_close(reason):
    print(f"Closed: {reason}")

def on_error(err):
    print(f"Error: {err}")

socket = websocketdata.NubraDataSocket(
    client=nubra,
    on_orderbook_data=on_orderbook_data,
    on_connect=on_connect,
    on_close=on_close,
    on_error=on_error,
)

socket.connect()
socket.subscribe([ref_id], data_type="orderbook")

time.sleep(RUN_SECONDS)
socket.unsubscribe([ref_id], data_type="orderbook")
socket.close()

if state["n"] == 0:
    print("No data received - market closed?")
