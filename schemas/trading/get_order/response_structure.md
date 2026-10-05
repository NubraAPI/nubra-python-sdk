# Schema Reference: Response Structure

Original source path: `trading/get_order/response_structure.py`

```python
class GetIntentOrdersResponse:
    # returned by trader.orders(...)
    orders: dict[str, list[IntentOrderResponse]]  # buckets: open, executed, cancelled, rejected, expired, gtt


class IntentOrderResponse:
    intentOrderId: int
    status: str | None
    isMulti: bool | None
    exchange: str | None
    legs: list[IntentOrderLeg]  # strategy orders only
    refId: int | None
    refData: RefDataWrapper | None
    orderQty: int | None
    filledQty: int | None
    deliveryType: str | None
    priceType: str | None
    validityType: str | None
    executionMode: str | None
    entryConfig: IntentOrderEntryConfig | None
    exitConfig: list[IntentOrderExitTrigger]
    side: str | None
    stratTags: list[str] | None
    entryPrice: int | None  # paise
    ltp: int | None
    orderPrice: int | None
    filledPrice: int | None
    rejectionMsg: str | None
    timestamps: IntentOrderTimestamps | None
    intentOrderType: str | None

# trader.get_order(id_or_ids) returns list[IntentOrderResponse]
```
