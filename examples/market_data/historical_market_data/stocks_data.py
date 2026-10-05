"""Fetch the last 3 days of 3-minute RELIANCE candles into a DataFrame.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: candle count and the last 10 candles (IST) with OHLC in rupees and volume
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

instruments = ["RELIANCE"]
response = md_instance.historical_data({
    "exchange": "NSE",
    "type": "STOCK",
    "values": instruments,
    "fields": ["open", "high", "low", "close", "cumulative_volume"],
    "startDate": (end - timedelta(days=3)).strftime(FMT),
    "endDate": end.strftime(FMT),
    "interval": "3m",
    "intraDay": False,
    "realTime": False
})

# historical_data() returns (does not raise) a NubraValidationError for a bad payload.
if isinstance(response, NubraValidationError):
    raise SystemExit(f"Invalid request payload: {response}")
if response is None or not response.result or not response.result[0].values:
    raise SystemExit("No data returned (check symbol, interval and date range)")

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
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].div(100)  # paise -> rupees
        df["symbol"] = symbol
        dfs[symbol] = df

df = dfs.get("RELIANCE")
if df is None or df.empty:
    print("RELIANCE: empty series (no candles in this range)")
else:
    print(f"RELIANCE: {len(df)} candles of 3m")
    print(df.tail(10))
