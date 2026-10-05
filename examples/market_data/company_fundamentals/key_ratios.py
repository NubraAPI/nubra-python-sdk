"""Fetch INFY key ratios (P/E, ROE, etc.) with TCS and WIPRO as peers.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: INFY fincode and the key ratios object
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.marketdata.validation import ExchangeEnum, FundamentalsTypeEnum
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

response = market_data.key_ratios(
    "INFY",
    exchange=ExchangeEnum.NSE,
    peers="TCS,WIPRO",
    fundamentals_type=FundamentalsTypeEnum.CONSOLIDATED,
)

print(response.result.keyratios_shareholding.fincode)
print(response.result.keyratios_shareholding.key_ratios)
print(response)
