"""Receive index ticks through the single on_market_data callback (central receiver).

Type: streaming
Needs: UAT login (PHONE_NO / MPIN in .env); market hours for ticks.
Expect: one line per tick, "[MarketData] NAME value(rupees) change%"; stops after 20 seconds.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time

from nubra_python_sdk.ticker import websocketdata
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

def rupees(paise):
    """Prices arrive as integer paise; show rupees. Missing values print as '-'."""
    return "-" if paise is None else f"{paise / 100:,.2f}"

ticks = {"n": 0}

def on_market_data(msg):
    ticks["n"] += 1
    # One central receiver gets every stream type; index ticks carry these fields.
    print("[MarketData]", getattr(msg, "indexname", None) or type(msg).__name__,
          rupees(getattr(msg, "index_value", None)),
          f"{getattr(msg, 'changepercent', None) or 0:+.2f}%")

def on_connect(msg):
    print("[status]", msg)

def on_close(reason):
    print(f"Closed: {reason}")

def on_error(err):
    print(f"Error: {err}")

socket = websocketdata.NubraDataSocket(
    client=nubra,
    on_market_data=on_market_data,
    on_connect=on_connect,
    on_close=on_close,
    on_error=on_error,
)

socket.connect()
socket.subscribe(["NIFTY", "HDFCBANK"], data_type="index", exchange="NSE")
socket.subscribe(["SENSEX"], data_type="index", exchange="BSE")

# Run for a short bounded time, then clean up (use socket.keep_running() to block forever instead).
time.sleep(20)
socket.unsubscribe(["NIFTY", "HDFCBANK"], data_type="index", exchange="NSE")
socket.unsubscribe(["SENSEX"], data_type="index", exchange="BSE")
socket.close()

if ticks["n"] == 0:
    print("No data received - market closed?")
else:
    print(f"Done: {ticks['n']} updates received.")
