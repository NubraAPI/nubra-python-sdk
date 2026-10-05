"""Stream live Greeks for the NIFTY at-the-money call option by ref_id.

Type: streaming
Needs: UAT login (PHONE_NO / MPIN in .env); market hours for ticks.
Expect: one line per update: LTP (rupees), IV, delta, gamma, theta, vega; stops after 20 seconds.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time

from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.ticker import websocketdata
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

market_data = MarketData(nubra)

# Pick the ATM call from the snapshot option chain and stream its Greeks by ref_id.
chain = market_data.option_chain("NIFTY", exchange="NSE").chain
atm_ce = next(
    (opt for opt in chain.ce if opt.strike_price == chain.at_the_money_strike),
    chain.ce[0],
)
ref_id = str(atm_ce.ref_id)

def rupees(paise):
    """Prices arrive as integer paise; show rupees. Missing values print as '-'."""
    return "-" if paise is None else f"{paise / 100:,.2f}"

ticks = {"n": 0}

def fmt(v):
    return "-" if v is None else f"{v:.4f}"

def on_greeks_data(msg):
    ticks["n"] += 1
    print("[GREEKS]", "LTP", rupees(getattr(msg, "last_traded_price", None)),
          "IV", fmt(getattr(msg, "iv", None)),
          "delta", fmt(getattr(msg, "delta", None)),
          "gamma", fmt(getattr(msg, "gamma", None)),
          "theta", fmt(getattr(msg, "theta", None)),
          "vega", fmt(getattr(msg, "vega", None)))

def on_connect(msg):
    print("[status]", msg)

def on_close(reason):
    print(f"Closed: {reason}")

def on_error(err):
    print(f"Error: {err}")

socket = websocketdata.NubraDataSocket(
    client=nubra,
    on_greeks_data=on_greeks_data,
    on_connect=on_connect,
    on_close=on_close,
    on_error=on_error,
)

socket.connect()
socket.subscribe([ref_id], data_type="greeks")

# Run for a short bounded time, then clean up (use socket.keep_running() to block forever instead).
time.sleep(20)
socket.unsubscribe([ref_id], data_type="greeks")
socket.close()

if ticks["n"] == 0:
    print("No data received - market closed?")
else:
    print(f"Done: {ticks['n']} updates received.")
