"""Fetch the last 7 days of daily candles for two NSE stocks.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: per symbol, a table of daily OHLC in rupees plus volume; clear message if empty
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

# Dates are UTC and relative to today so the example always returns data.
end = datetime.now(timezone.utc)
FMT = "%Y-%m-%dT%H:%M:%S.000Z"

result = market_data.historical_data({
    "exchange": "NSE",  # NSE, BSE or MCX
    "type": "STOCK",  # STOCK, INDEX, OPT or FUT
    "values": ["ASIANPAINT", "HDFCBANK"],  # symbols to fetch
    "fields": ["open", "high", "low", "close", "cumulative_volume"],  # series to return
    "startDate": (end - timedelta(days=7)).strftime(FMT),  # UTC ISO string
    "endDate": end.strftime(FMT),  # UTC ISO string
    "interval": "1d",  # 1s,1m,2m,3m,5m,15m,30m,1h,1d,1w; monthly is "1mt" on UAT (docs say "1mth", UAT rejects it)
    "intraDay": False,  # True means startDate is the current date
    "realTime": False  # accepted by the SDK; Nubra docs list it as "to be declared"; examples send False
})

# historical_data() returns (does not raise) a NubraValidationError for a bad payload.
if isinstance(result, NubraValidationError):
    raise SystemExit(f"Invalid request payload: {result}")
if result is None or not result.result or not result.result[0].values:
    raise SystemExit("No data returned (check symbols, interval and date range)")

print(f"Market time: {result.market_time}")
for item in result.result[0].values:
    for symbol, chart in item.items():
        if not chart.close:
            print(f"\n{symbol}: empty series (no candles in this range)")
            continue
        # Candle prices are integer paise; divide by 100 for rupees.
        df = pd.DataFrame(
            {
                "open": [p.value / 100 for p in chart.open],
                "high": [p.value / 100 for p in chart.high],
                "low": [p.value / 100 for p in chart.low],
                "close": [p.value / 100 for p in chart.close],
                "volume": [p.value for p in chart.cumulative_volume],
            },
            index=pd.to_datetime([p.timestamp for p in chart.close], unit="ns").date,
        )
        print(f"\n{symbol} (Rs)")
        print(df)
