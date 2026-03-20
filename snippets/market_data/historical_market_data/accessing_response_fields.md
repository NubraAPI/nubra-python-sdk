# Snippet: Accessing Response Fields

Original source path: `market_data/historical_market_data/accessing_response_fields.py`

```python
for data in result.result:
    print(data.exchange, data.type)
    for stock_data in data.values:
        for symbol, values in stock_data.items():
            print(symbol)
            print(values.close)
            print(values.high)
            print(values.low)
            print(values.open)
            print(values.cumulative_volume)
```
