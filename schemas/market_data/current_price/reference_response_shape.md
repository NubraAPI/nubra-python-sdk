# Schema Reference: Reference Response Shape

Original source path: `market_data/current_price/reference_response_shape.py`

```python
class CurrentPrice(BaseModel):
    change: Optional[float] = None
    message: str
    exchange: Optional[str] = None
    prev_close: Optional[int] = None
    price: Optional[int] = None
    indicative_close_price: Optional[int] = None  # in installed SDK, not in docs
```
