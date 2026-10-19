"""Compute PCR, max pain, OI concentration strikes and an IV-by-strike table from the NIFTY option chain.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: total PCR (open interest), the max-pain strike, the strikes holding the most call and put OI near
        ATM, and call/put IV (%) for the strikes around ATM.
Tested with: nubra-sdk 0.5.4 (UAT)

PCR = total put OI / total call OI.
Max pain = the expiry price at which the total intrinsic value owed to all open option holders is smallest.
OI concentration = the three strikes with the most OI on each side, within 10 strikes of ATM.
These are calculations on a snapshot, not predictions or trading signals.
"""
import numpy as np
import pandas as pd
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
result = MarketData(nubra).option_chain("NIFTY", exchange="NSE")
if result is None:
    raise SystemExit("No option chain returned (check symbol / exchange / expiry)")
chain = result.chain

FIELDS = {"open_interest": "oi", "iv": "iv"}


def side(options, tag):
    df = pd.DataFrame([o.model_dump() for o in options], columns=["strike_price", *FIELDS])
    return df.rename(columns={k: f"{tag}_{v}" for k, v in FIELDS.items()})


df = side(chain.ce, "call").merge(side(chain.pe, "put"), on="strike_price", how="outer").sort_values("strike_price")
df["strike"] = df["strike_price"] / 100  # paise -> rupees
df = df.drop(columns="strike_price").fillna({"call_oi": 0, "put_oi": 0}).reset_index(drop=True)
if df.empty or df["call_oi"].sum() == 0:
    raise SystemExit("Option chain has no open interest to analyse")

# 1. Put-call ratio by open interest.
pcr = df["put_oi"].sum() / df["call_oi"].sum()

# 2. Max pain: for each candidate expiry price, add up what call and put holders would be owed.
strikes = df["strike"].to_numpy()


def payout_at(price):
    call_value = (np.maximum(price - strikes, 0) * df["call_oi"].to_numpy()).sum()
    put_value = (np.maximum(strikes - price, 0) * df["put_oi"].to_numpy()).sum()
    return call_value + put_value


max_pain = strikes[int(np.argmin([payout_at(s) for s in strikes]))]

# 3. OI concentration: the three biggest OI strikes per side, within 10 strikes of ATM.
atm = chain.at_the_money_strike / 100
atm_pos = (df["strike"] - atm).abs().idxmin()
near = df.iloc[max(atm_pos - 10, 0): atm_pos + 11]
call_hot = near.nlargest(3, "call_oi")["strike"].tolist()
put_hot = near.nlargest(3, "put_oi")["strike"].tolist()

print(f"NIFTY expiry {chain.expiry} | spot {chain.current_price / 100:,.2f} | ATM {atm:,.0f}")
print(f"PCR (OI):   {pcr:.2f}")
print(f"Max pain:   {max_pain:,.0f}")
print(f"Most call OI near ATM: {[f'{s:,.0f}' for s in call_hot]}")
print(f"Most put OI near ATM:  {[f'{s:,.0f}' for s in put_hot]}")

# 4. IV by strike, five strikes either side of ATM. The API returns IV as a fraction (0.36 = 36%).
view = df.iloc[max(atm_pos - 5, 0): atm_pos + 6][["strike", "call_iv", "put_iv"]].copy()
view[["call_iv", "put_iv"]] = (view[["call_iv", "put_iv"]] * 100).round(2)
print("\nIV by strike (%):")
print(view.rename(columns={"call_iv": "Call IV %", "put_iv": "Put IV %"}).to_string(index=False))
