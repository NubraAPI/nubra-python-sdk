# Schema Reference: Sdk Surface

Original source path: `market_data/option_chain/sdk_surface.py`

```python
from nubra_python_sdk.marketdata.market_data import MarketData

# expiry: "YYYYMMDD"; exchange: "NSE" (default), "BSE" or "MCX"
MarketData.option_chain(instrument: str, expiry="", exchange=None)
```
