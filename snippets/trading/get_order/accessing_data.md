# Snippet: Accessing Data

Original source path: `trading/get_order/accessing_data.py`

```python
# trader.orders() returns GetIntentOrdersResponse: orders grouped by bucket.
all_orders = trader.orders()

for group_name, order_list in all_orders.orders.items():
    print(group_name)

    for order in order_list:
        print(order.intentOrderId)
        print(order.status)
        print(order.isMulti)
        print(order.refId)
        print(order.orderQty)
        print(order.filledQty)
        print(order.entryPrice)
        print(order.ltp)

        if order.entryConfig:
            print(order.entryConfig.entryTime)
            for condition in order.entryConfig.conditions or []:
                print(condition.kind, condition.threshold, condition.status)

        for trigger in order.exitConfig:
            print(trigger.exitTriggerKind)
            print(trigger.triggerPrice)
            print(trigger.limitPrice)
            print(trigger.trailJump)
            print(trigger.status)
```
