"""Fetch today's 5-minute NIFTY candles using intraDay=True.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: today's OHLC (index points), session high/low and change from the first open.
        Outside market hours or on holidays the series is empty and the script says so.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from datetime import datetime, timedelta, timezone

import pandas as pd
from nubra_python_sdk.interceptor.errors import NubraValidationError
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

end = datetime.now(timezone.utc)
FMT = "%Y-%m-%dT%H:%M:%S.000Z"

response = market_data.historical_data({
    "exchange": "NSE",
    "type": "INDEX",
    "values": ["NIFTY"],
    "fields": ["open", "high", "low", "close", "cumulative_volume"],
    "startDate": (end - timedelta(days=1)).strftime(FMT),
    "endDate": end.strftime(FMT),
    "interval": "5m",
    "intraDay": True,  # today's session only
    "realTime": False
})

if isinstance(response, NubraValidationError):
    raise SystemExit(f"Invalid request payload: {response}")
if response is None or not response.result or not response.result[0].values:
    raise SystemExit("No data returned (check symbol and interval)")

chart = response.result[0].values[0].get("NIFTY")
if chart is None or not chart.close:
    raise SystemExit("NIFTY: no intraday candles yet (market closed, holiday or before the open)")

df = pd.DataFrame(
    {
        "open": [p.value / 100 for p in chart.open],  # paise -> index points
        "high": [p.value / 100 for p in chart.high],
        "low": [p.value / 100 for p in chart.low],
        "close": [p.value / 100 for p in chart.close],
        "volume": [p.value for p in chart.cumulative_volume],
    },
    index=pd.to_datetime([p.timestamp for p in chart.close], unit="ns", utc=True).tz_convert("Asia/Kolkata"),
).sort_index()

print(df.tail(10))
change = (df["close"].iloc[-1] / df["open"].iloc[0] - 1) * 100
print(f"\n{len(df)} candles | high {df['high'].max():,.2f} | low {df['low'].min():,.2f} | "
      f"last {df['close'].iloc[-1]:,.2f} ({change:+.2f}% from first open)")
