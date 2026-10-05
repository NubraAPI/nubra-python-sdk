# Snippet: Accessing Data

Original source path: `portfolio/holdings/accessing_data.py`

```python
print(result.portfolio.clientCode)
print(result.portfolio.holdingStats.investedAmount)
print(result.portfolio.holdingStats.totalPnl)
print(result.portfolio.holdingStats.dayPnl)

if result.portfolio.holdings:
    holding = result.portfolio.holdings[0]
    print(holding.symbol)
    print(holding.quantity)
    print(holding.avgPrice)
    print(holding.prevClose)
    print(holding.lastTradedPrice)
    print(holding.currentValue)
    print(holding.netPnl)
    print(holding.marginBenefit)
    print(holding.availableToPledge)
```
