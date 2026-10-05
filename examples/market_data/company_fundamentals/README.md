# Company fundamentals examples

Default environment is UAT. Each script calls one `MarketData` method and prints typed result objects.

## Imports

```python
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.marketdata.validation import ExchangeEnum, FundamentalsTypeEnum, ResultTypeEnum
```

- `ResultTypeEnum`: `ANNUAL` ("A") or `QUARTERLY` ("Q"), used by `profit_loss`.
- `FundamentalsTypeEnum`: `STANDALONE` ("S") or `CONSOLIDATED` ("C").
- `ExchangeEnum`: these scripts import it from `nubra_python_sdk.marketdata.validation`. A second `ExchangeEnum` exists in `nubra_python_sdk.trading.trading_enum` (used by the trading examples). Both are str-enums with `NSE`, `BSE`, `MCX`, so the string `"NSE"` also works.

| File | What it does |
| --- | --- |
| `basic_usage.py` | Tour of every fundamentals call |
| `key_ratios.py` | INFY key ratios with peers |
| `cash_flow.py` | INFY cash flow statement |
| `balance_sheet.py` | HDFCBANK balance sheet |
| `profit_loss.py` | RELIANCE annual and quarterly P&L |
| `corporate_actions.py` | TCS corporate actions |
| `shareholding_pattern.py` | INFY shareholding (looks up `fincode` first) |
