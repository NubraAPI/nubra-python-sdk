"""Download 90 days of daily RELIANCE candles and save OHLC + daily returns to CSV.

Type: read-only (writes one local CSV file in the current directory)
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: last rows with OHLC in rupees and daily return %, then the CSV path
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from nubra_python_sdk.interceptor.errors import NubraValidationError
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

SYMBOL = "RELIANCE"
end = datetime.now(timezone.utc)  # UAT keeps ~7 months of history
FMT = "%Y-%m-%dT%H:%M:%S.000Z"

response = market_data.historical_data({
    "exchange": "NSE",
    "type": "STOCK",
    "values": [SYMBOL],
    "fields": ["open", "high", "low", "close", "cumulative_volume"],
    "startDate": (end - timedelta(days=90)).strftime(FMT),
    "endDate": end.strftime(FMT),
    "interval": "1d",
    "intraDay": False,
    "realTime": False
})

if isinstance(response, NubraValidationError):
    raise SystemExit(f"Invalid request payload: {response}")
if response is None or not response.result or not response.result[0].values:
    raise SystemExit("No data returned (check symbol and date range)")

chart = response.result[0].values[0].get(SYMBOL)
if chart is None or not chart.close:
    raise SystemExit(f"{SYMBOL}: empty series (no daily candles in this range)")

df = pd.DataFrame(
    {
        "open": [p.value / 100 for p in chart.open],  # paise -> rupees
        "high": [p.value / 100 for p in chart.high],
        "low": [p.value / 100 for p in chart.low],
        "close": [p.value / 100 for p in chart.close],
        "volume": [p.value for p in chart.cumulative_volume],
    },
    index=pd.to_datetime([p.timestamp for p in chart.close], unit="ns").date,
).sort_index()
df.index.name = "date"
df["daily_return_%"] = (df["close"].pct_change() * 100).round(2)

print(df.tail(10))
print(f"\n{len(df)} candles | best day {df['daily_return_%'].max()}% | worst day {df['daily_return_%'].min()}%")

out = Path(f"{SYMBOL.lower()}_daily_ohlc.csv")
df.to_csv(out)
print(f"Saved {out.resolve()}")
