"""Tour of all company fundamentals calls: ratios, cash flow, balance sheet, P&L, corporate actions, shareholding.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: key ratios, then each statement printed as returned by the SDK
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.marketdata.validation import (
    ExchangeEnum,
    FundamentalsTypeEnum,
    ResultTypeEnum,
)
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

ratios = market_data.key_ratios("INFY")
print("KEY RATIOS:")
print(ratios)

cash_flow = market_data.cash_flow("INFY", limit=5)
print("CASH FLOW:")
print(cash_flow)

balance_sheet = market_data.balance_sheet("HDFCBANK", limit=5)
print("BALANCE SHEET:")
print(balance_sheet)

profit_loss = market_data.profit_loss(
    "RELIANCE",
    result_type=ResultTypeEnum.QUARTERLY,
    limit=8,
)
print("PROFIT AND LOSS:")
print(profit_loss)

actions = market_data.corp_actions("TCS")
print("CORPORATE ACTIONS:")
print(actions)

# shareholding_pattern() takes the company fincode, not a symbol.
fincode = ratios.result.keyratios_shareholding.fincode
shareholding = market_data.shareholding_pattern(fincode, limit=4)
print("SHAREHOLDING PATTERN:")
print(shareholding)
