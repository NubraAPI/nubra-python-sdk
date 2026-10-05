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

Field notes (from the SDK models, `nubra_python_sdk.marketdata.validation`):

| Field | Type | Unit |
|---|---|---|
| `price` | int or None | paise |
| `prev_close` | int or None | paise |
| `indicative_close_price` | int or None | unit not confirmed; present in the installed SDK, not in the Nubra docs |
| `change` | float or None | percent change versus `prev_close` |
| `message` | str | status text, e.g. `current price` |
| `exchange` | str or None | `NSE`, `BSE` or `MCX` |

`current_price()` can return `None`, or an object with `price=None`, for an unknown symbol.
