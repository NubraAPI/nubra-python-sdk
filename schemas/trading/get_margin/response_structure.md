# Schema Reference: Response Structure

Original source path: `trading/get_margin/response_structure.py`

`trader.get_margin({"requestType": "NEW", "orders": [...]})` returns a `FundsRequiredResp`. Every field is optional and can be `None`. The request orders use the same dicts as `create_order`.

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


class IntentBrokerageResp:
    chargesFloat: dict[str, float] | None
    totalChargesFloat: float | None


class IntentOrderIcebergParamsResp:
    numberOfLegs: int | None
    maxQtyPerLeg: int | None


class TradingSlot:
    startTime: str | None
    endTime: str | None
```

## Fields

| Field | Type | Unit | Notes |
| --- | --- | --- | --- |
| `totalFundsRequired` | int | paise | Funds needed for the request. Compare with `portfolio.funds().portFundsAndMargin.netMarginAvailable` (also paise). |
| `marginInfo.totalMargin` | int | paise | Total margin for the request. |
| `marginInfo.message` | str | text | Message returned with the margin, if any. |
| `marginInfo.maxAllowedQty` | int | quantity | |
| `marginInfo.cncSellAllowedQty` | int | quantity | |
| `marginInfo.availableQty` | int | quantity | |
| `marginInfo.edisDoneQty` | int | quantity | |
| `marginInfo.edisRemainingQty` | int | quantity | |
| `brokerageInfo.chargesFloat` | dict[str, float] | | Charges keyed by name. |
| `brokerageInfo.totalChargesFloat` | float | | Total of the charges. |
| `willDefaultBePlacedAsAmo` | bool | | |
| `refIdAmoMap` | dict[int, bool] | | Keyed by `refId`. |
| `openOrders` | int | count | |
| `icebergInfo` | object | | `numberOfLegs`, `maxQtyPerLeg` (both int). |
| `tradingSlot` | object | | `startTime`, `endTime` (both str). |
| `willBeAutoSliced` | bool | | |
| `code` | int | | |

The examples in `examples/trading/get_margin/` read only `totalFundsRequired`, `marginInfo.totalMargin` and `marginInfo.message`, and print them as rupees (paise / 100). Real UAT output:

```
LTP: Rs 1316.30
Funds required: Rs 329.62
Total margin:   Rs 329.07
```
