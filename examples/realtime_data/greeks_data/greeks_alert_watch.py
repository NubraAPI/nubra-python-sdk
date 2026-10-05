"""Watch NIFTY ATM call and put Greeks and print an ALERT when IV or premium moves past a threshold.

Type: streaming
Needs: UAT login (PHONE_NO / MPIN in .env); market hours for ticks.
Expect: a status line per leg about every 2 seconds, plus "ALERT" lines when a threshold is crossed
        versus the last alert level; stops after 25 seconds, or "No data received - market closed?".
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time

from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.ticker import websocketdata
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

RUN_SECONDS = 25
IV_MOVE_ALERT = 0.01       # alert if IV moves 1% (relative) from the reference reading
PREMIUM_MOVE_ALERT = 0.02  # alert if LTP moves 2% (relative) from the reference reading

# Pick the ATM call and put from the snapshot chain; stream both by ref_id.
chain = MarketData(nubra).option_chain("NIFTY", exchange="NSE").chain
atm = chain.at_the_money_strike
ce = next((o for o in chain.ce if o.strike_price == atm), chain.ce[0])
pe = next((o for o in chain.pe if o.strike_price == atm), chain.pe[0])
labels = {ce.ref_id: "CE", pe.ref_id: "PE"}
ref_ids = [str(ce.ref_id), str(pe.ref_id)]

ref = {}  # ref_id -> {"iv": reference IV, "ltp": reference LTP}
last_print = {}
ticks = {"n": 0}

def moved(first, now, limit):
    return bool(first) and now is not None and abs(now - first) / abs(first) >= limit

def on_greeks_data(msg):
    ticks["n"] += 1
    rid = getattr(msg, "ref_id", None)
    label = labels.get(rid, str(rid))
    iv, ltp = getattr(msg, "iv", None), getattr(msg, "last_traded_price", None)
    base = ref.setdefault(rid, {"iv": iv, "ltp": ltp})
    if base["iv"] is None:
        base["iv"] = iv
    if base["ltp"] is None:
        base["ltp"] = ltp
    now = time.time()
    if now - last_print.get(rid, 0) >= 2:
        last_print[rid] = now
        delta = getattr(msg, "delta", None)
        print(f"[{label}] LTP {'-' if ltp is None else f'{ltp / 100:,.2f}'} | IV {iv} | "
              f"delta {'-' if delta is None else f'{delta:.3f}'}")
    if moved(base["iv"], iv, IV_MOVE_ALERT):
        print(f"ALERT [{label}] IV moved from {base['iv']} to {iv}")
        base["iv"] = iv  # re-arm from the new level
    if moved(base["ltp"], ltp, PREMIUM_MOVE_ALERT):
        print(f"ALERT [{label}] premium moved from {base['ltp'] / 100:,.2f} to {ltp / 100:,.2f}")
        base["ltp"] = ltp

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
socket.subscribe(ref_ids, data_type="greeks")

time.sleep(RUN_SECONDS)
socket.unsubscribe(ref_ids, data_type="greeks")
socket.close()

if ticks["n"] == 0:
    print("No data received - market closed?")
