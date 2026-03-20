# Schema Reference: Reference Response Shape

Original source path: `market_data/market_quotes/reference_response_shape.py`

```python
class OrderBookWrapper:
    orderBook: OrderBook

class OrderBook:
    ref_id: int
    timestamp: int
    bid: list[OrderLevel]
    ask: list[OrderLevel]
    last_traded_price: int
    last_traded_quantity: int
    volume: int

class OrderLevel:
    price: int
    quantity: int
    num_orders: int
```
