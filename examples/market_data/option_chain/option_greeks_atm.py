"""Print IV and Greeks (delta, gamma, theta, vega) with OI for the strikes around ATM in the NIFTY chain.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: a call table and a put table for the strikes within a window of ATM (prices in rupees), plus PCR.
Tested with: nubra-sdk 0.5.4 (UAT)

Greeks come from the chain as delivered by the API. They can differ slightly from other platforms because
IV is back-solved from the last traded price, so the underlying used (spot or futures), the interest-rate and
dividend inputs, and the age of the last trade (illiquid strikes) all move the numbers.
Compare liquid near-ATM strikes only; far OTM strikes trade rarely and are stale more often.
"""
import pandas as pd
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

WINDOW = 5  # strikes either side of ATM

# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
result = MarketData(nubra).option_chain("NIFTY", exchange="NSE")
if result is None:
    raise SystemExit("No option chain returned (check symbol / exchange / expiry)")
chain = result.chain

COLUMNS = ["strike", "ltp", "iv", "delta", "gamma", "theta", "vega", "oi"]


def side_table(options):
    rows = [{
        "strike": o.strike_price / 100,  # paise -> rupees
        "ltp": None if o.last_traded_price is None else o.last_traded_price / 100,
        "iv": o.iv, "delta": o.delta, "gamma": o.gamma, "theta": o.theta, "vega": o.vega,
        "oi": o.open_interest,
    } for o in options]
    return pd.DataFrame(rows, columns=COLUMNS).sort_values("strike").reset_index(drop=True)


calls, puts = side_table(chain.ce), side_table(chain.pe)
if calls.empty or puts.empty:
    raise SystemExit("Option chain has no strikes")
atm = chain.at_the_money_strike / 100
pos = (calls["strike"] - atm).abs().idxmin()
lo, hi = max(pos - WINDOW, 0), pos + WINDOW + 1

print(f"NIFTY expiry {chain.expiry} | spot {chain.current_price / 100:,.2f} | ATM {atm:,.0f}")
print("\nCalls")
print(calls.iloc[lo:hi].round(4).to_string(index=False))
print("\nPuts")
put_pos = (puts["strike"] - atm).abs().idxmin()
print(puts.iloc[max(put_pos - WINDOW, 0): put_pos + WINDOW + 1].round(4).to_string(index=False))

call_oi, put_oi = calls["oi"].fillna(0).sum(), puts["oi"].fillna(0).sum()
if call_oi:
    print(f"\nPCR (OI): {put_oi / call_oi:.2f}")
