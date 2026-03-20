import pandas as pd
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
md_instance = MarketData(nubra)

instruments = ["NIFTY"]
response = md_instance.historical_data({
    "exchange": "NSE",
    "type": "INDEX",
    "values": instruments,
    "fields": ["open", "high", "low", "close", "cumulative_volume"],
    "startDate": "2016-02-01T11:01:57.000Z",
    "endDate": "2026-02-04T06:18:57.000Z",
    "interval": "1mt",
    "intraDay": False,
    "realTime": False
})

def tsp_values(tsp_list):
    return [p.value for p in tsp_list]

dfs = {}
for instrument_dict in response.result[0].values:
    for symbol, stock_chart in instrument_dict.items():
        index = pd.to_datetime(
            [p.timestamp for p in stock_chart.open],
            unit="ns"
        )
        df = pd.DataFrame(
            {
                "open": tsp_values(stock_chart.open),
                "high": tsp_values(stock_chart.high),
                "low": tsp_values(stock_chart.low),
                "close": tsp_values(stock_chart.close),
                "volume": tsp_values(stock_chart.cumulative_volume),
            },
            index=index
        )
        df.sort_index(inplace=True)
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].div(100)
        df["symbol"] = symbol
        dfs[symbol] = df

print(dfs["NIFTY"])
