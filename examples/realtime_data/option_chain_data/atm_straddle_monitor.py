"""Live NIFTY ATM straddle price: ATM call LTP + ATM put LTP from the option-chain stream.

Type: streaming
Needs: UAT login (PHONE_NO / MPIN in .env); market hours for ticks.
Expect: about one line per second: spot, ATM strike, CE, PE, straddle (rupees); stops after 25 seconds
        with a low/high summary, or "No data received - market closed?".
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time

from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.ticker import websocketdata
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

RUN_SECONDS = 25

# Resolve the nearest expiry from the snapshot chain (expiry is YYYYMMDD).
expiry = MarketData(nubra).option_chain("NIFTY", exchange="NSE").chain.expiry
key = f"NIFTY:{expiry}"

def rupees(paise):
    return "-" if paise is None else f"{paise / 100:,.2f}"

state = {"n": 0, "last_print": 0.0, "values": []}

def on_option_data(msg):
    state["n"] += 1
    atm = getattr(msg, "at_the_money_strike", None)
    ce = next((o for o in (getattr(msg, "ce", None) or []) if o.strike_price == atm), None)
    pe = next((o for o in (getattr(msg, "pe", None) or []) if o.strike_price == atm), None)
    ce_ltp, pe_ltp = getattr(ce, "last_traded_price", None), getattr(pe, "last_traded_price", None)
    if ce_ltp is None or pe_ltp is None:
        return  # ATM legs have not both ticked yet
    straddle = ce_ltp + pe_ltp
    state["values"].append(straddle)
    now = time.time()
    if now - state["last_print"] >= 1:  # throttle to ~1 line per second
        state["last_print"] = now
        print(f"spot {rupees(getattr(msg, 'current_price', None))} | ATM {rupees(atm)} | "
              f"CE {rupees(ce_ltp)} + PE {rupees(pe_ltp)} = straddle {rupees(straddle)}")

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

time.sleep(RUN_SECONDS)
socket.unsubscribe([key], data_type="option", exchange="NSE")
socket.close()

values = state["values"]
if state["n"] == 0:
    print("No data received - market closed?")
elif not values:
    print("Chain updates arrived but ATM CE/PE prices were missing.")
else:
    print(f"Straddle range over the window: low {rupees(min(values))} / high {rupees(max(values))}")
