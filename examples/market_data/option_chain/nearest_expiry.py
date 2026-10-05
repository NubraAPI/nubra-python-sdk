"""Pick the nearest upcoming NIFTY expiry from the chain and fetch that expiry explicitly.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: all expiries, the nearest one on/after today, and its ATM strike and spot
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from datetime import date

from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)


def nearest_expiry(expiries, today=None):
    """Earliest expiry (YYYYMMDD string) that is today or later, else None."""
    today = (today or date.today()).strftime("%Y%m%d")
    upcoming = sorted(e for e in expiries if e >= today)
    return upcoming[0] if upcoming else None


first = market_data.option_chain("NIFTY", exchange="NSE")
if first is None:
    raise SystemExit("No option chain returned (check symbol / exchange)")

print(f"All expiries: {first.chain.all_expiries}")
expiry = nearest_expiry(first.chain.all_expiries)
if expiry is None:
    raise SystemExit("No upcoming expiry found")

# expiry is a YYYYMMDD string.
result = market_data.option_chain("NIFTY", expiry=expiry, exchange="NSE")
if result is None:
    raise SystemExit(f"No option chain returned for expiry {expiry}")
chain = result.chain
print(f"Nearest expiry: {expiry} ({chain.asset})")
print(f"Spot Rs {chain.current_price / 100:,.2f} | ATM strike {chain.at_the_money_strike / 100:,.0f}")
