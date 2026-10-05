# Schema Reference: Sdk Surface

Original source path: `market_data/historical_market_data/sdk_surface.py`

```python
from nubra_python_sdk.marketdata.market_data import MarketData

# request keys: exchange, type ("STOCK" | "INDEX" | "OPT" | "FUT" | "CHAIN"),
# values, fields, startDate, endDate, interval, intraDay, realTime
# interval: 1s, 1m, 2m, 3m, 5m, 15m, 30m, 1h, 1d, 1w, 1mth
MarketData.historical_data(request: dict | list[dict])
```
