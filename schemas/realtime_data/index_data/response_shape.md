# Schema Reference: Response Shape

Original source path: `realtime_data/index_data/response_shape.py`

```python
class IndexDataWrapper:
    indexname: str
    exchange: str
    timestamp: int
    index_value: int
    high_index_value: int
    low_index_value: int
    volume: int
    changepercent: float
    tick_volume: int
    prev_close: int
    volume_oi: int | None
```
