# Schema Reference: Response Shape

Original source path: `realtime_data/ohlcv_data/response_shape.py`

```python
class OhlcvDataWrapper:
    indexname: str
    exchange: str
    interval: str
    timestamp: int
    open: int
    high: int
    low: int
    close: int
    bucket_volume: int
    tick_volume: int
    cumulative_volume: int
    bucket_timestamp: int
```
