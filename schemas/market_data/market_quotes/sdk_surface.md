# Schema Reference: Sdk Surface

Original source path: `market_data/market_quotes/sdk_surface.py`

```python
from nubra_python_sdk.marketdata.market_data import MarketData

# ref_id comes from InstrumentData.get_instrument_by_symbol(...).ref_id
MarketData.quote(ref_id: int, levels: int)
```
