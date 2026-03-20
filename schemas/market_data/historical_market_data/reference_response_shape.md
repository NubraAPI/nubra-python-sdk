# Schema Reference: Reference Response Shape

Original source path: `market_data/historical_market_data/reference_response_shape.py`

```python
class MarketChartsResponse:
    market_time: str
    message: str
    result: list[ChartData]

class ChartData:
    exchange: str
    type: str
    values: list[dict[str, StockChart]]

class StockChart:
    open: list[TimeSeriesPoint] | None
    high: list[TimeSeriesPoint] | None
    low: list[TimeSeriesPoint] | None
    close: list[TimeSeriesPoint] | None
    cumulative_volume: list[TimeSeriesPoint] | None
    cumulative_oi: list[TimeSeriesPoint] | None
    theta: list[TickPoint] | None
    delta: list[TickPoint] | None
    gamma: list[TickPoint] | None
    vega: list[TickPoint] | None
    iv_mid: list[TickPoint] | None

class TimeSeriesPoint:
    timestamp: int
    value: int

class TickPoint:
    timestamp: int | None
    value: float | None
```
