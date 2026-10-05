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
