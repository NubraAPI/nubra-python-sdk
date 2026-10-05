"""Fetch INFY shareholding pattern for the last 4 quarters (looks up the fincode first).

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: quarter dates and holding percentages
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.marketdata.validation import ExchangeEnum
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

# shareholding_pattern() takes a company fincode, not a symbol.
ratios = market_data.key_ratios("INFY", exchange=ExchangeEnum.NSE)
fincode = ratios.result.keyratios_shareholding.fincode

response = market_data.shareholding_pattern(fincode, limit=4, offset=0)

print(response.result.shareholding_pattern.dates)
print(response.result.shareholding_pattern.data)
print(response)
