# Snippet: Accessing Data

Original source path: `portfolio/holdings/accessing_data.py`

```python
print(result.portfolio.client_code)
print(result.portfolio.holding_stats.invested_amount)
print(result.portfolio.holding_stats.total_pnl)
print(result.portfolio.holding_stats.day_pnl)

if result.portfolio.holdings:
    holding = result.portfolio.holdings[0]
    print(holding.symbol)
    print(holding.quantity)
    print(holding.avg_price)
    print(holding.prev_close)
    print(holding.last_traded_price)
    print(holding.current_value)
    print(holding.net_pnl)
    print(holding.margin_benefit)
    print(holding.available_to_pledge)
```
