"""Fetch the latest price for the nearest CRUDEOIL and GOLD MCX futures.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: contract name, price, previous close and % change per commodity
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from datetime import date

from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# MCX is available on UAT. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)
market_data = MarketData(nubra)

mcx = instruments.get_instruments_dataframe(exchange="MCX")
today = int(date.today().strftime("%Y%m%d"))


def nearest_future(asset):
    # Nearest future that has not expired yet, e.g. FUT_CRUDEOIL_20261019.
    futures = mcx[(mcx["asset"] == asset) & (mcx["derivative_type"] == "FUT") & (mcx["expiry"].astype(int) > today)]
    if futures.empty:
        return None
    return futures.sort_values("expiry").iloc[0]["stock_name"]


def rs(paise):
    # The API returns integer paise; show rupees.
    return "n/a" if paise is None else f"Rs {paise / 100:,.2f}"


for asset in ("CRUDEOIL", "GOLD"):
    # MCX futures are quoted by their full contract name, not the bare asset name.
    symbol = nearest_future(asset)
    if symbol is None:
        print(f"{asset}: no live future found in the MCX instrument master")
        continue
    p = market_data.current_price(symbol, exchange="MCX")
    if p is None or p.price is None:
        print(f"{symbol}: no price returned")
    else:
        print(f"{symbol}: {rs(p.price)} | prev close {rs(p.prev_close)} | change {p.change}%")
