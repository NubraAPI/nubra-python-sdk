# Schema Reference: Response Shape

Original source path: `realtime_data/order_book_data/response_shape.py`

```python
class OrderBookWrapper:
    ref_id: int
    timestamp: int
    last_traded_price: int
    last_traded_quantity: int
    volume: int
    bids: list[Orders]
    asks: list[Orders]

class Orders:
    price: int
    quantity: int
    num_orders: int
```
