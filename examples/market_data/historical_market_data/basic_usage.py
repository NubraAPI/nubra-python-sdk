from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

result = market_data.historical_data({
    "exchange": "NSE",
    "type": "STOCK",
    "values": ["ASIANPAINT", "TATAMOTORS"],
    "fields": ["open", "high", "low", "close", "cumulative_volume"],
    "startDate": "2025-04-19T11:01:57.000Z",
    "endDate": "2025-04-24T06:13:57.000Z",
    "interval": "1d",
    "intraDay": False,
    "realTime": False
})

print(result.message)
print(result.market_time)
