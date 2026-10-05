# Schema Reference: Sdk Surface

Original source path: `get_instruments/sdk_surface.py`

`exchange` can be `NSE`, `BSE` or `MCX`. If omitted, the default is `NSE`
(`get_instrument_by_ref_id` resolves globally when `exchange` is omitted).

```python
from nubra_python_sdk.refdata.instruments import InstrumentData

InstrumentData.get_instruments_dataframe(exchange=None)
InstrumentData.get_instrument_by_ref_id(ref_id, exchange=None)
InstrumentData.get_instrument_by_symbol(instr, exchange=None)
InstrumentData.get_instrument_by_nubra_name(nubra_name, exchange=None)
InstrumentData.get_instruments(
    exchange=None,
    asset=None,
    derivative_type=None,
    asset_type=None,
    expiry=None,
    strike_price=None,
    option_type=None,
    isin=None,
)
InstrumentData.get_instruments_by_pattern(request)
```
