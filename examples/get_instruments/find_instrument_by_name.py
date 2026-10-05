"""Find NSE stocks by partial name or symbol (e.g. "HDFC").
Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env
Expect: a table of matching cash-market instruments with ref_id and lot size.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

QUERY = "HDFC"  # any part of the symbol / name, case-insensitive

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)

df = instruments.get_instruments_dataframe(exchange="NSE")
cash = df[df["derivative_type"] == "STOCK"]
hits = cash[
    cash["stock_name"].str.contains(QUERY, case=False, na=False)
    | cash["asset"].str.contains(QUERY, case=False, na=False)
]
if hits.empty:
    raise SystemExit(f"No NSE stock matches '{QUERY}'.")

print(f"{len(hits)} match(es) for '{QUERY}':")
print(hits[["ref_id", "stock_name", "asset", "lot_size", "tick_size"]].head(20).to_string(index=False))
# tick_size is in paise (5 = Rs 0.05).

# Then resolve one exactly. Not-found comes back as a dict with "msg".
exact = instruments.get_instrument_by_symbol(hits.iloc[0]["stock_name"], exchange="NSE")
if isinstance(exact, dict):
    raise SystemExit(exact["msg"])
print("First match ref_id:", exact.ref_id)
