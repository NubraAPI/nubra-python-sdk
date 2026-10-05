"""Compare the two nearest NIFTY expiries: ATM straddle, ATM IV, PCR and OI walls.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: a side-by-side table (rupees) for the nearest and next expiry
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from datetime import date

import pandas as pd
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

first = market_data.option_chain("NIFTY", exchange="NSE")
if first is None:
    raise SystemExit("No option chain returned (check symbol / exchange)")

today = date.today().strftime("%Y%m%d")
expiries = sorted(e for e in first.chain.all_expiries if e >= today)[:2]
if len(expiries) < 2:
    raise SystemExit(f"Need two upcoming expiries, found {expiries}")


def summarise(expiry):
    result = market_data.option_chain("NIFTY", expiry=expiry, exchange="NSE")  # YYYYMMDD string
    if result is None:
        return None
    chain = result.chain
    atm = chain.at_the_money_strike
    ce = {o.strike_price: o for o in chain.ce}
    pe = {o.strike_price: o for o in chain.pe}
    row = {"spot": chain.current_price / 100, "ATM strike": atm / 100}
    if atm in ce and atm in pe:
        row["ATM straddle Rs"] = (ce[atm].last_traded_price + pe[atm].last_traded_price) / 100
        row["ATM IV (avg)"] = (ce[atm].iv + pe[atm].iv) / 2 if ce[atm].iv and pe[atm].iv else None
    ce_oi = sum(o.open_interest or 0 for o in chain.ce)
    pe_oi = sum(o.open_interest or 0 for o in chain.pe)
    row["PCR (OI)"] = round(pe_oi / ce_oi, 2) if ce_oi else None
    if ce_oi:
        row["Resistance (max call OI)"] = max(chain.ce, key=lambda o: o.open_interest or 0).strike_price / 100
    if pe_oi:
        row["Support (max put OI)"] = max(chain.pe, key=lambda o: o.open_interest or 0).strike_price / 100
    return row


rows = {e: summarise(e) for e in expiries}
missing = [e for e, r in rows.items() if r is None]
if missing:
    raise SystemExit(f"No option chain returned for expiry {missing}")
print(pd.DataFrame(rows).to_string())
