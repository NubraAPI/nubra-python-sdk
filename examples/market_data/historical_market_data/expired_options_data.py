"""Fetch daily candles and greeks for two expired NIFTY weekly option contracts.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: OHLC (rupees), volume, greeks, IV and OI per contract. UAT usually returns
        empty series for expired contracts; the script then says so. PROD has full data.
Note: the contracts and dates are fixed on purpose (they identify specific expired options).
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import pandas as pd
from nubra_python_sdk.interceptor.errors import NubraValidationError
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", 1000)
pd.set_option("display.max_colwidth", None)
pd.set_option("display.width", 0)

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
md_instance = MarketData(nubra)

# Expired weekly contracts keep their history. UAT may return empty series; PROD has the full data.
instruments = ["NIFTY2692222500CE", "NIFTY2691522500CE"]
response = md_instance.historical_data({
    "exchange": "NSE",
    "type": "OPT",
    "values": instruments,
    "fields": [
        "open", "high", "low", "close", "cumulative_volume",
        "theta", "delta", "gamma", "vega", "iv_mid", "cumulative_oi"
    ],
    "startDate": "2026-09-01T03:45:00.000Z",
    "endDate": "2026-09-22T10:00:00.000Z",
    "interval": "1d",
    "intraDay": False,
    "realTime": False
})

# historical_data() returns (does not raise) a NubraValidationError for a bad payload.
if isinstance(response, NubraValidationError):
    raise SystemExit(f"Invalid request payload: {response}")
if response is None or not response.result or not response.result[0].values:
    raise SystemExit("No data returned (check contract names and date range)")

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
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].div(100)  # paise -> rupees
        df["symbol"] = symbol
        dfs[symbol] = df

for symbol in instruments:
    df = dfs.get(symbol)
    print(f"{symbol} Historical data with greeks")
    if df is None or df.empty:
        print("  empty series (expired contracts are often not available on UAT)")
    else:
        print(df.head())
    print()
