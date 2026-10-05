# Snippet: Accessing Data

Original source path: `portfolio/positions/accessing_data.py`

```python
print(result.portfolio.clientCode)
print(result.portfolio.positionStats.totalPnl)
print(result.portfolio.positionStats.totalPnlChg)

if result.portfolio.positions:
    first_position = result.portfolio.positions[0]
    print(first_position.symbol)
    print(first_position.buyQuantity)
    print(first_position.sellQuantity)
    print(first_position.netQuantity)
    print(first_position.pnl)
```
