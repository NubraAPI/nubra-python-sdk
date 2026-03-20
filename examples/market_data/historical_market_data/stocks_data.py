import pandas as pd
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
md_instance = MarketData(nubra)

instruments = ["RELIANCE"]
response = md_instance.historical_data({
    "exchange": "NSE",
    "type": "STOCK",
    "values": instruments,
    "fields": ["open", "high", "low", "close", "cumulative_volume"],
    "startDate": "2026-02-05T03:30:00.000Z",
    "endDate": "2026-02-05T11:30:00.000Z",
    "interval": "3m",
    "intraDay": False,
    "realTime": False
})

def tsp_list_to_series(tsp_list):
    idx = pd.to_datetime(
        [p.timestamp for p in tsp_list],
        unit="ns",
        utc=True
    ).tz_convert("Asia/Kolkata")
    return pd.Series(
        data=[p.value for p in tsp_list],
        index=idx
    )

dfs = {}
for instrument_dict in response.result[0].values:
    for symbol, stock_chart in instrument_dict.items():
        df = pd.DataFrame({
            "open": tsp_list_to_series(stock_chart.open),
            "high": tsp_list_to_series(stock_chart.high),
            "low": tsp_list_to_series(stock_chart.low),
            "close": tsp_list_to_series(stock_chart.close),
            "volume": tsp_list_to_series(stock_chart.cumulative_volume),
        })
        df.sort_index(inplace=True)
        df["symbol"] = symbol
        dfs[symbol] = df

print(dfs["RELIANCE"])
