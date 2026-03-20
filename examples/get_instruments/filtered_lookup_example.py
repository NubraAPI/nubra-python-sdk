from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)

results = instruments.get_instruments(
    exchange="NSE",
    asset="HDFCBANK",
    derivative_type="STOCK",
)

print(results)
