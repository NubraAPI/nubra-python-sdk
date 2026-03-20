# Snippet: Accessing Data

Original source path: `portfolio/positions/accessing_data.py`

```python
print(result_v2.portfolio.client_code)
print(result_v2.portfolio.position_stats.total_pnl)
print(result_v2.portfolio.position_stats.total_pnl_chg)

if result_v2.portfolio.positions:
    first_position = result_v2.portfolio.positions[0]
    print(first_position.symbol)
    print(first_position.buy_quantity)
    print(first_position.sell_quantity)
    print(first_position.net_quantity)
    print(first_position.pnl)
```
