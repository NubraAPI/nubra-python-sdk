"""List upcoming expiries and the lot size for an underlying.
Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env
Expect: one row per future/option expiry with days left, lot size and contract count.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from datetime import date, datetime

from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

UNDERLYING = "NIFTY"  # try BANKNIFTY, RELIANCE ...
EXCHANGE = "NSE"      # or "MCX" with e.g. "CRUDEOIL"

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)

df = instruments.get_instruments_dataframe(exchange=EXCHANGE)
fno = df[(df["asset"] == UNDERLYING) & (df["derivative_type"].isin(["FUT", "OPT"]))].copy()
if fno.empty:
    raise SystemExit(f"No derivatives found for {UNDERLYING} on {EXCHANGE}.")

fno["expiry"] = fno["expiry"].astype(int)
today = date.today()
print(f"{UNDERLYING} ({EXCHANGE}) expiries:")
print(f"{'Expiry':<12}{'Days':>6}{'Lot size':>10}{'Contracts':>11}  Types")
for expiry, grp in fno.groupby("expiry"):
    exp_date = datetime.strptime(str(expiry), "%Y%m%d").date()
    if exp_date < today:
        continue
    types = "/".join(sorted(grp["derivative_type"].unique()))
    print(f"{exp_date.isoformat():<12}{(exp_date - today).days:>6}"
          f"{int(grp['lot_size'].iloc[0]):>10}{len(grp):>11}  {types}")
