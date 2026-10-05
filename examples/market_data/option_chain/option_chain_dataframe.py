"""Turn the NIFTY option chain into a DataFrame with ATM, PCR, OI walls and IV skew.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: ATM-centred chain table (rupees), PCR, max-OI call/put strikes
        (resistance / support) and an OTM put vs call IV skew line
Tested with: nubra-sdk 0.5.4 (UAT)

PCR = total put open interest / total call open interest (OI, not volume).
IV skew = OTM put IV 3 strikes below ATM minus OTM call IV 3 strikes above ATM.
These are calculations, not trading signals.
"""
import pandas as pd
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

result = market_data.option_chain("NIFTY", exchange="NSE")
if result is None:
    raise SystemExit("No option chain returned (check symbol / exchange / expiry)")
chain = result.chain

FIELDS = {"last_traded_price": "ltp", "open_interest": "oi", "iv": "iv", "volume": "volume"}


def side(options, tag):
    df = pd.DataFrame([o.model_dump() for o in options], columns=["strike_price", *FIELDS])
    return df.rename(columns={k: f"{tag}_{v}" for k, v in FIELDS.items()})


df = side(chain.ce, "ce").merge(side(chain.pe, "pe"), on="strike_price", how="outer").sort_values("strike_price")
if df.empty:
    raise SystemExit("Option chain has no strikes")

# Prices and strikes come in paise: convert to rupees for reading.
df["strike"] = df["strike_price"] / 100
df["ce_ltp"] /= 100
df["pe_ltp"] /= 100
df = df.drop(columns="strike_price").reset_index(drop=True)
atm = chain.at_the_money_strike / 100
spot = chain.current_price / 100

print(f"NIFTY expiry {chain.expiry} | spot {spot:,.2f} | ATM strike {atm:,.0f}")

# Show 5 strikes either side of ATM.
atm_pos = (df["strike"] - atm).abs().idxmin()
view = df.iloc[max(atm_pos - 5, 0): atm_pos + 6]
print(view[["ce_oi", "ce_iv", "ce_ltp", "strike", "pe_ltp", "pe_iv", "pe_oi"]].to_string(index=False))

# Put-call ratio by open interest (> 1 leans bullish, < 1 leans bearish).
total_ce_oi, total_pe_oi = df["ce_oi"].sum(), df["pe_oi"].sum()
if total_ce_oi:
    print(f"\nPCR (OI): {total_pe_oi / total_ce_oi:.2f}  (put OI {total_pe_oi:,.0f} / call OI {total_ce_oi:,.0f})")

# Highest OI strikes act as resistance (calls) and support (puts).
if df["ce_oi"].max() > 0:
    print(f"Resistance (max call OI): {df.loc[df['ce_oi'].idxmax(), 'strike']:,.0f}")
if df["pe_oi"].max() > 0:
    print(f"Support    (max put OI):  {df.loc[df['pe_oi'].idxmax(), 'strike']:,.0f}")

# IV skew: OTM put IV (3 strikes below ATM) minus OTM call IV (3 strikes above ATM).
put_iv = df["pe_iv"].iloc[atm_pos - 3] if atm_pos >= 3 else None
call_iv = df["ce_iv"].iloc[atm_pos + 3] if atm_pos + 3 < len(df) else None
if pd.notna(put_iv) and pd.notna(call_iv):
    print(f"IV skew (OTM put - OTM call, 3 strikes out): {put_iv - call_iv:+.2f}  (put {put_iv:.2f} vs call {call_iv:.2f})")
else:
    print("IV skew: not enough strikes with IV data")
