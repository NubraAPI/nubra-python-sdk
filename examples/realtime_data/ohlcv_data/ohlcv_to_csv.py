"""Record live NIFTY 1-minute OHLCV candle updates to a CSV file.

Type: streaming
Needs: UAT login (PHONE_NO / MPIN in .env); market hours for ticks.
Expect: writes output/ohlcv_NIFTY_1m.csv next to this script (prices in rupees) and prints the row count;
        stops after 25 seconds, or "No data received - market closed?".
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import csv
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from nubra_python_sdk.ticker import websocketdata
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

RUN_SECONDS = 25
SYMBOL = "NIFTY"
IST = timezone(timedelta(hours=5, minutes=30))
out_path = Path(__file__).resolve().parent / "output" / f"ohlcv_{SYMBOL}_1m.csv"
out_path.parent.mkdir(exist_ok=True)

def rupees(paise):
    return "" if paise is None else round(paise / 100, 2)

def clock(ts):
    """Epoch timestamp (ns, us, ms or s) -> HH:MM:SS in IST; blank if missing."""
    if not ts:
        return ""
    while ts > 1e11:
        ts /= 1000
    return datetime.fromtimestamp(ts, IST).strftime("%H:%M:%S")

csv_file = open(out_path, "w", newline="", encoding="utf-8")
writer = csv.writer(csv_file)
writer.writerow(["time_ist", "open", "high", "low", "close", "volume"])
rows = {"n": 0}

def on_ohlcv_data(msg):
    writer.writerow([
        clock(getattr(msg, "bucket_timestamp", None) or getattr(msg, "timestamp", None)),
        rupees(getattr(msg, "open", None)),
        rupees(getattr(msg, "high", None)),
        rupees(getattr(msg, "low", None)),
        rupees(getattr(msg, "close", None)),
        getattr(msg, "bucket_volume", None) or 0,
    ])
    rows["n"] += 1

def on_connect(msg):
    print("[status]", msg)

def on_close(reason):
    print(f"Closed: {reason}")

def on_error(err):
    print(f"Error: {err}")

socket = websocketdata.NubraDataSocket(
    client=nubra,
    on_ohlcv_data=on_ohlcv_data,
    on_connect=on_connect,
    on_close=on_close,
    on_error=on_error,
)

socket.connect()
socket.subscribe([SYMBOL], data_type="ohlcv", interval="1m", exchange="NSE")

time.sleep(RUN_SECONDS)
socket.unsubscribe([SYMBOL], data_type="ohlcv", interval="1m", exchange="NSE")
socket.close()
csv_file.close()

if rows["n"] == 0:
    print("No data received - market closed?")
else:
    print(f"Wrote {rows['n']} rows to {out_path}")
