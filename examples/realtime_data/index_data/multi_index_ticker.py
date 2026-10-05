"""Multi-index ticker table: latest value and change% for several indices, refreshed every 5 seconds.

Type: streaming
Needs: UAT login (PHONE_NO / MPIN in .env); market hours for ticks.
Expect: a small table printed every 5 seconds (values in rupees); stops after 25 seconds.
        Indices that never tick show "waiting"; with no ticks at all: "No data received - market closed?".
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time

from nubra_python_sdk.ticker import websocketdata
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

RUN_SECONDS = 25
NSE_INDICES = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
BSE_INDICES = ["SENSEX"]

latest = {}  # index name -> (value in paise, change %)
ticks = {"n": 0}

def on_index_data(msg):
    ticks["n"] += 1
    name = getattr(msg, "indexname", None)
    if not name:
        return
    prev_value, prev_chg = latest.get(name, (None, None))
    value = getattr(msg, "index_value", None)
    chg = getattr(msg, "changepercent", None)
    latest[name] = (value if value is not None else prev_value, chg if chg is not None else prev_chg)

def show_table():
    print(f"{'INDEX':<12}{'VALUE':>14}{'CHG %':>9}")
    for name in NSE_INDICES + BSE_INDICES:
        value, chg = latest.get(name, (None, None))
        if value is None:
            print(f"{name:<12}{'waiting':>14}")
        else:
            print(f"{name:<12}{value / 100:>14,.2f}{(chg or 0):>+9.2f}")
    print()

def on_connect(msg):
    print("[status]", msg)

def on_close(reason):
    print(f"Closed: {reason}")

def on_error(err):
    print(f"Error: {err}")

socket = websocketdata.NubraDataSocket(
    client=nubra,
    on_index_data=on_index_data,
    on_connect=on_connect,
    on_close=on_close,
    on_error=on_error,
)

socket.connect()
socket.subscribe(NSE_INDICES, data_type="index", exchange="NSE")
socket.subscribe(BSE_INDICES, data_type="index", exchange="BSE")

for _ in range(RUN_SECONDS // 5):
    time.sleep(5)
    if ticks["n"]:
        show_table()

socket.unsubscribe(NSE_INDICES, data_type="index", exchange="NSE")
socket.unsubscribe(BSE_INDICES, data_type="index", exchange="BSE")
socket.close()

if ticks["n"] == 0:
    print("No data received - market closed?")
