# Schema Reference: Reference Response Shape

Original source path: `market_data/company_fundamentals/reference_response_shape.py`

All fields are Optional. Every response also has `message: str | None`.

```python
# key_ratios() -> result.keyratios_shareholding
class KeyRatiosShareholding:
    symbol: str
    fincode: int
    ltp: float
    close_price: float
    key_ratios: KeyRatios                       # p_e_ratio, p_b_ratio, roe, roa, roce, eps, market_cap, ...
    shareholding_keys: ShareholdingKeys         # promoter, mf, retail_other, fiis, other_domestic_insti
    technical_indicators: TechnicalIndicators   # ema12d, ema26d, macd, rsi, mfi, ...

# cash_flow() / balance_sheet() / profit_loss()
# -> result.cash_flow | result.balance_sheet | result.profit_loss
class FinancialsData:
    dates: list[str]          # e.g. "202603"; quarterly P&L e.g. "2024Q1"
    data: list[FinancialRow]

class FinancialRow:
    label: str
    is_key_ratio: bool        # True -> ratio-style float values
    values: list[FinancialValue]

class FinancialValue:
    date: str
    value: Any                # scaled int, float for ratio rows, or None
    children: list[FinancialChildValue] | None

# corp_actions() -> result.corporate_actions
class CorporateAction:
    corp_action_name, action_type, upcoming_event, record_date, execution_date,
    ratio1, ratio2, dividend_type, amount, ...  # full list in installed SDK validation.py

# shareholding_pattern() -> result.shareholding_pattern
class ShareholdingPatternData:
    dates: list[str]
    data: list[ShareholdingRow]   # label, is_key_ratio, values

class ShareholdingValueEntry:
    date: str
    value: float                  # percentage
    shareholding_children: list[ShareholdingEntity] | None  # label, value, children
```
