# Snippet: V3 Callbacks

Fill events (`trade_fill` present) go to `on_trade_update`; all other intent-order events go to `on_order_update`.

```python
def on_order_update(msg):
    order = msg.intent_order_response
    if order:
        print(order.intent_order_id, order.order_status, order.rejection_msg)

def on_trade_update(msg):
    order = msg.intent_order_response
    fill = order.trade_fill if order else None
    if fill:
        print(fill.ref_id, fill.trade_qty, fill.trade_price)
```
