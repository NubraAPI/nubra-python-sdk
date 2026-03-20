# Schema Reference: Response Shape

Original source path: `realtime_data/greeks_data/response_shape.py`

```python
class OptionData:
    ref_id: int
    timestamp: int
    strike_price: int
    lot_size: int
    last_traded_price: int | None
    last_traded_price_change: float | None
    iv: float | None
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None
    volume: int | None
    open_interest: int | None
    previous_open_interest: int | None
```
