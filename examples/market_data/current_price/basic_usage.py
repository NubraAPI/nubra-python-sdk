from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

nifty_price = market_data.current_price("NIFTY")
reliance_price = market_data.current_price("RELIANCE")

print(nifty_price)
print(reliance_price)
