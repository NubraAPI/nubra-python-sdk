"""Fetch 12 months of monthly NIFTY index candles.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: DataFrame of monthly OHLC in rupees (index points) plus volume
Note: UAT keeps ~7 months of history, so expect fewer than 12 rows there.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from datetime import datetime, timedelta, timezone
import pandas as pd
from nubra_python_sdk.interceptor.errors import NubraValidationError
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
md_instance = MarketData(nubra)

# Dates are UTC and relative to today so the example always returns data.
end = datetime.now(timezone.utc)
FMT = "%Y-%m-%dT%H:%M:%S.000Z"

instruments = ["NIFTY"]
response = md_instance.historical_data({
    "exchange": "NSE",
    "type": "INDEX",
    "values": instruments,
    "fields": ["open", "high", "low", "close", "cumulative_volume"],
    "startDate": (end - timedelta(days=365)).strftime(FMT),
    "endDate": end.strftime(FMT),
    "interval": "1mt",  # monthly candles: UAT accepts "1mt" (the docs say "1mth")
    "intraDay": False,
    "realTime": False
})

# historical_data() returns (does not raise) a NubraValidationError for a bad payload.
if isinstance(response, NubraValidationError):
    raise SystemExit(f"Invalid request payload: {response}")
if response is None or not response.result or not response.result[0].values:
    raise SystemExit("No data returned (check symbol, interval and date range)")

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

for symbol, df in dfs.items():
    if df.empty:
        print(f"{symbol}: empty series (no candles in this range)")
    else:
        print(df)
