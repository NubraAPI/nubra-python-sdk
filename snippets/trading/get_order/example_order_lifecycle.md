# Snippet: Example Order Lifecycle

Original source path: `trading/get_order/example_order_lifecycle.py`

```python
# Fetch details before modify
before_mod = trader.get_order(order_id)
print("Before Modify:")
print(before_mod)

# Modify order
modify_res = trader.modify_order_v2(
    order_id=order_id,
    request={
        "order_price": 134400,
        "order_qty": 1,
        "exchange": "NSE",
        "order_type": "ORDER_TYPE_STOPLOSS",
        "price_type": "LIMIT",
        "algo_params": {"trigger_price": 134390},
    },
)
print("Modify Response:")
print(modify_res)

# Fetch details after modify
after_mod = trader.get_order(order_id)
print("After Modify:")
print(after_mod)
```
