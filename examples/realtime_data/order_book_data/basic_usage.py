"""Stream the live order book (market depth) for HDFCBANK by ref_id.

Type: streaming
Needs: UAT login (PHONE_NO / MPIN in .env); market hours for ticks.
Expect: one line per update: LTP, best bid / best ask (rupees) with quantities; stops after 20 seconds.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time

from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.ticker import websocketdata
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

instruments = InstrumentData(nubra)
instrument = instruments.get_instrument_by_symbol("HDFCBANK", exchange="NSE")
if isinstance(instrument, dict):  # not found -> {"msg": "..."}
    raise SystemExit(f"Instrument lookup failed: {instrument.get('msg')}")
ref_id = instrument.ref_id

def rupees(paise):
    """Prices arrive as integer paise; show rupees. Missing values print as '-'."""
    return "-" if paise is None else f"{paise / 100:,.2f}"

ticks = {"n": 0}

def on_orderbook_data(msg):
    ticks["n"] += 1
    bid = (getattr(msg, "bids", None) or [None])[0]
    ask = (getattr(msg, "asks", None) or [None])[0]
    print("[ORDERBOOK]", "LTP", rupees(getattr(msg, "last_traded_price", None)),
          "| bid", rupees(getattr(bid, "price", None)), "x", getattr(bid, "quantity", "-"),
          "| ask", rupees(getattr(ask, "price", None)), "x", getattr(ask, "quantity", "-"))

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
socket.subscribe([str(ref_id)], data_type="orderbook")

# Run for a short bounded time, then clean up (use socket.keep_running() to block forever instead).
time.sleep(20)
socket.unsubscribe([str(ref_id)], data_type="orderbook")
socket.close()

if ticks["n"] == 0:
    print("No data received - market closed?")
else:
    print(f"Done: {ticks['n']} updates received.")
