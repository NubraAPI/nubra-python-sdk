"""Fetch the latest price for an NSE index and stock.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: one line per symbol with price, previous close and % change in rupees
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

nifty_price = market_data.current_price("NIFTY", exchange="NSE")
reliance_price = market_data.current_price("RELIANCE", exchange="NSE")


def rs(paise):
    # The API returns integer paise; show rupees.
    return "n/a" if paise is None else f"Rs {paise / 100:,.2f}"


for name, p in (("NIFTY", nifty_price), ("RELIANCE", reliance_price)):
    if p is None or p.price is None:
        print(f"{name}: no price returned (check symbol / exchange)")
    else:
        print(f"{name}: {rs(p.price)} | prev close {rs(p.prev_close)} | change {p.change}%")
