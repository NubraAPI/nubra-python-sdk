"""List TCS corporate actions (dividends, splits, bonus).

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: name, type, upcoming flag and record date per action
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.marketdata.validation import ExchangeEnum
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

response = market_data.corp_actions("TCS", exchange=ExchangeEnum.NSE)

for action in response.result.corporate_actions:
    print(action.corp_action_name)
    print(action.action_type)
    print(action.upcoming_event)
    print(action.record_date)

print(response)
