import pandas as pd
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", 1000)
pd.set_option("display.max_colwidth", None)
pd.set_option("display.width", 0)

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
md_instance = MarketData(nubra)

instruments = ["NIFTY2611326000CE", "NIFTY25D2326000CE"]
response = md_instance.historical_data({
    "exchange": "NSE",
    "type": "OPT",
    "values": instruments,
    "fields": [
        "open", "high", "low", "close", "cumulative_volume",
        "theta", "delta", "gamma", "vega", "iv_mid", "cumulative_oi"
    ],
    "startDate": "2025-12-01T11:01:57.000Z",
    "endDate": "2026-01-14T06:13:57.000Z",
    "interval": "1d",
    "intraDay": False,
    "realTime": False
})

def tsp_list_to_series(tsp_list):
    return pd.Series(
        data=[p.value for p in tsp_list],
        index=pd.to_datetime([p.timestamp for p in tsp_list], unit="ns")
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
            "theta": tsp_list_to_series(stock_chart.theta),
            "delta": tsp_list_to_series(stock_chart.delta),
            "gamma": tsp_list_to_series(stock_chart.gamma),
            "vega": tsp_list_to_series(stock_chart.vega),
            "iv_mid": tsp_list_to_series(stock_chart.iv_mid),
            "cumulative_oi": tsp_list_to_series(stock_chart.cumulative_oi),
        })
        df.sort_index(inplace=True)
        df["symbol"] = symbol
        dfs[symbol] = df

print(f"{instruments[0]} Historical data with greeks")
print(dfs[instruments[0]].head())
print()
print(f"{instruments[1]} Historical data with greeks")
print(dfs[instruments[1]].head())
