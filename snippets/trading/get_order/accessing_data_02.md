# Snippet: Accessing Data 02

Original source path: `trading/get_order/accessing_data_02.py`

```python
# trader.get_order(...) returns a list of orders for the given intentOrderId(s).
orders = trader.get_order(order_id)

for order in orders:
    print(order.intentOrderId)
    print(order.refId)
    print(order.status)
    print(order.filledPrice)
    print(order.orderPrice)
    print(order.ltp)
    print(order.exchange)
    print(order.priceType)
    print(order.validityType)
    print(order.rejectionMsg)

    if order.refData:
        print(order.refData.refId)
        print(order.refData.asset)
        print(order.refData.displayName)

    # Strategy orders (isMulti=True) carry their legs here.
    for leg in order.legs:
        print(leg.refId, leg.unitQty, leg.orderQty, leg.filledQty, leg.filledPrice)
```
