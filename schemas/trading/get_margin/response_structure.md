# Schema Reference: Response Structure

Original source path: `trading/get_margin/response_structure.py`

```python
class FundsRequiredResp:
    # returned by trader.get_margin(...)
    code: int | None
    marginInfo: IntentMarginResp | None
    brokerageInfo: IntentBrokerageResp | None
    totalFundsRequired: int | None
    willDefaultBePlacedAsAmo: bool | None
    refIdAmoMap: dict[int, bool] | None
    openOrders: int | None
    icebergInfo: IntentOrderIcebergParamsResp | None
    tradingSlot: TradingSlot | None
    willBeAutoSliced: bool | None


class IntentMarginResp:
    totalMargin: int | None
    message: str | None
    maxAllowedQty: int | None
    cncSellAllowedQty: int | None
    availableQty: int | None
    edisDoneQty: int | None
    edisRemainingQty: int | None
```
