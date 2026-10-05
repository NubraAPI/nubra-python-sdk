# Snippet: Example Order Lifecycle

Original source path: `trading/get_order/example_order_lifecycle.py`

```python
# order_id is the intentOrderId returned by create_order(...).orders[0].intentOrderId

# Fetch details before modify
before_mod = trader.get_order(order_id)
print("Before Modify:")
print(before_mod)

# Modify order (acknowledgement only)
modify_res = trader.modify_orders_sentinel({
    "orderId": order_id,
    "qty": 1,
    "entryPrice": 134400,  # paise
    "deliveryType": "IDAY",
    "priceType": "LIMIT",
    "validityType": "DAY",
    "executionMode": "ENTRY",
})
print("Modify Response:")
print(modify_res)

# Fetch details after modify
after_mod = trader.get_order(order_id)
print("After Modify:")
print(after_mod)

# Cancel order (acknowledgement only)
cancel_res = trader.cancel_orders_sentinel([{"orderId": order_id}])
print("Cancel Response:")
print(cancel_res)
```
