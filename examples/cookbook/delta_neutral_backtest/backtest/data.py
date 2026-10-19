"""Historical 1-minute data access through the Nubra SDK, with an optional CSV cache.

Read-only: only MarketData.historical_data() is called. Prices come back as
integer paise and are converted to rupees here.
"""
import time
from pathlib import Path

import pandas as pd
from nubra_python_sdk.interceptor.errors import NubraValidationError
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

OPT_FIELDS = ["close", "delta", "gamma", "l1bid", "l1ask"]
FUT_FIELDS = ["close", "l1bid", "l1ask"]
INDEX_FIELDS = ["close"]
PRICE_COLS = ("close", "bid", "ask")
MAX_BATCH = 5            # the API accepts up to 5 symbols per request
MIN_INTERVAL_SEC = 1.1   # stay under the 60 requests/minute limit
FMT = "%Y-%m-%dT%H:%M:%S.000Z"
IST_OFFSET = pd.Timedelta(hours=5, minutes=30)


def ist_to_utc(day, hh: int, mm: int) -> pd.Timestamp:
    """IST wall-clock on `day` -> naive UTC timestamp (the SDK works in UTC)."""
    return pd.Timestamp(day).normalize() + pd.Timedelta(hours=hh, minutes=mm) - IST_OFFSET


class HistoricalData:
    def __init__(self, env: NubraEnv = NubraEnv.UAT, exchange: str = "NSE", cache_dir: str | None = None):
        # UAT by default. To use production, switch to NubraEnv.PROD.
        self.market_data = MarketData(InitNubraSdk(env, env_creds=True))
        self.exchange = exchange
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._last_call = 0.0
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    # -- low level -------------------------------------------------------
    def _fetch(self, instrument_type: str, symbols: list, fields: list,
               start: pd.Timestamp, end: pd.Timestamp, interval: str = "1m") -> dict:
        """Returns {symbol: DataFrame indexed by naive-UTC time, prices in rupees}."""
        wait = MIN_INTERVAL_SEC - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()
        response = self.market_data.historical_data({
            "exchange": self.exchange,
            "type": instrument_type,        # INDEX, OPT or FUT
            "values": symbols,
            "fields": fields,
            "startDate": start.strftime(FMT),
            "endDate": end.strftime(FMT),
            "interval": interval,
            "intraDay": False,
            "realTime": False,
        })
        # historical_data() returns (does not raise) a NubraValidationError for a bad payload.
        if isinstance(response, NubraValidationError):
            raise RuntimeError(f"Invalid request payload: {response}")
        out: dict = {}
        if response is None or not response.result or not response.result[0].values:
            return out
        for item in response.result[0].values:
            for symbol, chart in item.items():
                cols = {}
                for f in fields:
                    points = getattr(chart, f, None) or []
                    cols[f] = pd.Series([p.value for p in points],
                                        index=pd.to_datetime([p.timestamp for p in points], unit="ns"),
                                        dtype="float64")
                df = pd.DataFrame(cols).sort_index().rename(columns={"l1bid": "bid", "l1ask": "ask"})
                for c in PRICE_COLS:
                    if c in df.columns:
                        df[c] = df[c] / 100.0   # paise -> rupees
                out[symbol] = df
        return out

    def _cache_path(self, kind: str, symbol: str, start, end):
        if not self.cache_dir:
            return None
        return self.cache_dir / f"{kind}_{symbol}_{start:%Y%m%d%H%M}_{end:%Y%m%d%H%M}.csv"

    def _read_cache(self, path):
        if path is not None and path.exists():
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            return True, (df if not df.empty else None)
        return False, None

    # -- public ----------------------------------------------------------
    def _single(self, kind: str, symbol: str, fields: list, start, end):
        path = self._cache_path(kind, symbol, start, end)
        hit, df = self._read_cache(path)
        if hit:
            return df
        df = self._fetch(kind, [symbol], fields, start, end).get(symbol)
        if path is not None and df is not None:
            df.to_csv(path)
        return df

    def index_bars(self, underlying: str, start, end):
        return self._single("INDEX", underlying, INDEX_FIELDS, start, end)

    def futures_bars(self, symbol: str, start, end):
        return self._single("FUT", symbol, FUT_FIELDS, start, end)

    def option_bars(self, symbols: list, start, end) -> dict:
        """{symbol: DataFrame or None}; uncached symbols are fetched in batches of <= 5."""
        result: dict = {}
        missing = []
        for s in symbols:
            hit, df = self._read_cache(self._cache_path("OPT", s, start, end))
            if hit:
                result[s] = df
            else:
                missing.append(s)
        for i in range(0, len(missing), MAX_BATCH):
            chunk = missing[i:i + MAX_BATCH]
            frames = self._fetch("OPT", chunk, OPT_FIELDS, start, end)
            for s in chunk:
                df = frames.get(s)
                result[s] = df
                path = self._cache_path("OPT", s, start, end)
                if path is not None and df is not None:
                    df.to_csv(path)
        return result
