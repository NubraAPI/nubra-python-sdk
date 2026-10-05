"""Filter the instrument master by exchange, asset and derivative type.
Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env
Expect: number of matches and the first records.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)

results = instruments.get_instruments(
    exchange="NSE",
    asset="HDFCBANK",
    derivative_type="STOCK",
)

if not results:
    raise SystemExit("No instruments matched these filters.")
print(f"{len(results)} match(es). First: {results[0]}")
