from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Use NubraEnv.UAT for testing and NubraEnv.UAT for production.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

# Reuse the authenticated client across modules.
# Example:
# instruments = InstrumentData(nubra)
# market_data = MarketData(nubra)
# trader = NubraTrader(nubra, version="V2")
