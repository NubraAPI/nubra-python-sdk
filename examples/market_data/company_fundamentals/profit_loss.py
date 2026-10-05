"""Fetch RELIANCE annual (5) and quarterly (8) profit and loss.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: annual and quarterly P&L as returned by the SDK
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.marketdata.validation import ResultTypeEnum
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

annual = market_data.profit_loss("RELIANCE", result_type=ResultTypeEnum.ANNUAL, limit=5)
quarterly = market_data.profit_loss("RELIANCE", result_type=ResultTypeEnum.QUARTERLY, limit=8)

print("ANNUAL PROFIT AND LOSS:")
print(annual)

print("QUARTERLY PROFIT AND LOSS:")
print(quarterly)
