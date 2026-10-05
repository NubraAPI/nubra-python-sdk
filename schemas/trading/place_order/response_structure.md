# Schema Reference: Response Structure

Original source path: `trading/place_order/response_structure.py`

```python
class CreateIntentOrderResponse:
    # returned by trader.create_order(...)
    orders: list[IntentOrderResponse]  # one item per single order; one item for a strategy order

# Use orders[i].intentOrderId for get_order, modify_orders_sentinel and cancel_orders_sentinel.
# modify_orders_sentinel and cancel_orders_sentinel return a raw acknowledgement dict.
```
