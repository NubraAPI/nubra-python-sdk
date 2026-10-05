"""Find the nearest-expiry futures contract for NSE and MCX underlyings.
Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env
Expect: for each underlying, the contract name, expiry, lot size, tick size (paise) and ref_id.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from datetime import date, datetime

import pandas as pd

from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)
today = int(date.today().strftime("%Y%m%d"))


def nearest_future(exchange, asset):
    df = instruments.get_instruments_dataframe(exchange=exchange)
    fut = df[(df["asset"] == asset) & (df["derivative_type"] == "FUT") & (pd.to_numeric(df["expiry"], errors="coerce") >= today)]
    if fut.empty:
        return None
    return fut.sort_values("expiry").iloc[0]


for exchange, asset in [("NSE", "HDFCBANK"), ("MCX", "CRUDEOIL"), ("MCX", "GOLD")]:
    row = nearest_future(exchange, asset)
    if row is None:
        print(f"{exchange} {asset}: no live futures contract found")
        continue
    expiry = datetime.strptime(str(int(row["expiry"])), "%Y%m%d").date()
    # MCX contracts are addressed by full name (e.g. FUT_CRUDEOIL_20261019), never bare "GOLD".
    print(f"{exchange} {asset}: {row['stock_name']} | expiry {expiry} | lot {int(row['lot_size'])} | tick {int(row['tick_size'])} paise | ref_id {int(row['ref_id'])}")
