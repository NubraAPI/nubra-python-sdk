# Schema Reference: Reference Response Shape

Original source path: `market_data/market_quotes/reference_response_shape.py`

```python
class OrderBookWrapper:
    orderBook: OrderBook

class OrderBook:
    ref_id: int | None
    timestamp: int | None
    bid: list[OrderLevel] | None
    ask: list[OrderLevel] | None
    last_traded_price: int
    last_traded_quantity: int
    volume: int | None

class OrderLevel:
    price: int | None
    quantity: int | None
    num_orders: int | None
```

Field notes (from the SDK models, `nubra_python_sdk.marketdata.validation`):

| Field | Type | Unit |
|---|---|---|
| `orderBook.ref_id` | int or None | instrument id |
| `orderBook.timestamp` | int or None | timestamp as returned by the API (unit not documented in the SDK) |
| `orderBook.bid`, `orderBook.ask` | list of `OrderLevel` or None | best level first |
| `orderBook.last_traded_price` | int | paise |
| `orderBook.last_traded_quantity` | int | quantity |
| `orderBook.volume` | int or None | quantity |
| `OrderLevel.price` | int or None | paise |
| `OrderLevel.quantity` | int or None | quantity |
| `OrderLevel.num_orders` | int or None | number of orders at the level |

`quote()` returns `None` when the API sends back no usable data (for example for an unknown `ref_id`). Check for `None` before reading fields.
