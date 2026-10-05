"""Fetch the last 5 years of INFY consolidated cash flow.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: statement dates and rows (values as returned by the API)
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.marketdata.validation import ExchangeEnum, FundamentalsTypeEnum
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

response = market_data.cash_flow(
    "INFY",
    exchange=ExchangeEnum.NSE,
    fundamentals_type=FundamentalsTypeEnum.CONSOLIDATED,
    limit=5,
    offset=0,
)

print(response.result.cash_flow.dates)
print(response.result.cash_flow.data)
print(response)
