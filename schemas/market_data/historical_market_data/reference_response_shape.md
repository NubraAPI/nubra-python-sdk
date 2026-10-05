# Schema Reference: Reference Response Shape

Original source path: `market_data/historical_market_data/reference_response_shape.py`

```python
class MarketChartsResponse:
    market_time: str | None
    message: str
    result: list[ChartData] | None

class ChartData:
    exchange: str
    type: str
    values: list[dict[str, StockChart]] | None

class StockChart:
    # Every series is a list or None; only requested fields are populated.
    open, high, low, close: list[TimeSeriesPoint]
    tick_volume: list[TimeSeriesPoint]
    cumulative_volume: list[TimeSeriesPoint]
    cumulative_volume_premium: list[TimeSeriesPoint]
    cumulative_oi: list[TimeSeriesPoint]
    cumulative_call_oi: list[TimeSeriesPoint]
    cumulative_put_oi: list[TimeSeriesPoint]
    cumulative_fut_oi: list[TimeSeriesPoint]
    l1bid: list[TimeSeriesPoint]
    l1ask: list[TimeSeriesPoint]
    value: list[TimeSeriesPoint]  # INDEX spot price (price x 100)
    theta, delta, gamma, vega: list[TickPoint]
    iv_bid, iv_ask, iv_mid: list[TickPoint]
    cumulative_volume_delta: list[TickPoint]

class TimeSeriesPoint:
    timestamp: int | None  # nanoseconds
    value: int

class TickPoint:
    timestamp: int | None
    value: float | None
```
