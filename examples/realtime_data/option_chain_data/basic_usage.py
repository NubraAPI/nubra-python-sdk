"""Stream the live NIFTY option chain for the nearest expiry (resolved from a snapshot).

Type: streaming
Needs: UAT login (PHONE_NO / MPIN in .env); market hours for ticks.
Expect: one line per update: expiry, spot, ATM strike, CE/PE counts, ATM CE/PE LTP (rupees); stops after 20 seconds.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time

from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.ticker import websocketdata
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

market_data = MarketData(nubra)

# Resolve a live expiry from the snapshot chain (expiry is YYYYMMDD) instead of hard-coding one.
expiry = market_data.option_chain("NIFTY", exchange="NSE").chain.expiry
key = f"NIFTY:{expiry}"

def rupees(paise):
    """Prices arrive as integer paise; show rupees. Missing values print as '-'."""
    return "-" if paise is None else f"{paise / 100:,.2f}"

ticks = {"n": 0}

def on_option_data(msg):
    ticks["n"] += 1
    atm = getattr(msg, "at_the_money_strike", None)
    calls, puts = (getattr(msg, "ce", None) or []), (getattr(msg, "pe", None) or [])
    ce = next((o for o in calls if o.strike_price == atm), None)
    pe = next((o for o in puts if o.strike_price == atm), None)
    print("[OPTION]", getattr(msg, "expiry", "?"),
          "spot", rupees(getattr(msg, "current_price", None)),
          "ATM", rupees(atm),
          f"CE/PE count {len(calls)}/{len(puts)}",
          "ATM CE", rupees(getattr(ce, "last_traded_price", None)),
          "ATM PE", rupees(getattr(pe, "last_traded_price", None)))

def on_connect(msg):
    print("[status]", msg)

def on_close(reason):
    print(f"Closed: {reason}")

def on_error(err):
    print(f"Error: {err}")

socket = websocketdata.NubraDataSocket(
    client=nubra,
    on_option_data=on_option_data,
    on_connect=on_connect,
    on_close=on_close,
    on_error=on_error,
)

socket.connect()
socket.subscribe([key], data_type="option", exchange="NSE")

# Run for a short bounded time, then clean up (use socket.keep_running() to block forever instead).
time.sleep(20)
socket.unsubscribe([key], data_type="option", exchange="NSE")
socket.close()

if ticks["n"] == 0:
    print("No data received - market closed?")
else:
    print(f"Done: {ticks['n']} updates received.")
