# Schema Reference: Sdk Surface

Original source path: `market_data/company_fundamentals/sdk_surface.py`

```python
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.marketdata.validation import (
    ExchangeEnum,            # NSE, BSE, MCX
    FundamentalsTypeEnum,    # STANDALONE ("S"), CONSOLIDATED ("C")
    ResultTypeEnum,          # ANNUAL ("A"), QUARTERLY ("Q")
)

MarketData.key_ratios(symbol, exchange=None, peers=None, fundamentals_type=None, limit=None, offset=None)
MarketData.cash_flow(symbol, exchange=None, fundamentals_type=None, limit=None, offset=None)
MarketData.balance_sheet(symbol, exchange=None, fundamentals_type=None, limit=None, offset=None)
MarketData.profit_loss(symbol, exchange=None, fundamentals_type=None, result_type=None, limit=None, offset=None)
MarketData.corp_actions(symbol, exchange=None)
MarketData.shareholding_pattern(fincode: int, limit=None, offset=None)
```
