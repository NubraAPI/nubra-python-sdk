# Snippet: Accessing Financial Statements

Original source path: `market_data/company_fundamentals/accessing_financial_statements.py`

```python
# Same shape for cash_flow(), balance_sheet() and profit_loss().
# Use result.cash_flow, result.balance_sheet or result.profit_loss accordingly.
statement = market_data.cash_flow("INFY", limit=5).result.cash_flow

print(statement.dates)  # period keys such as "202603"

for row in statement.data:
    print(row.label, row.is_key_ratio)
    for point in row.values:
        print(point.date, point.value)
```
