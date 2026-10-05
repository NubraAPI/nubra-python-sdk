# Snippet: Accessing Key Ratios

Original source path: `market_data/company_fundamentals/accessing_key_ratios.py`

```python
data = market_data.key_ratios("INFY").result.keyratios_shareholding

print(data.symbol)
print(data.fincode)
print(data.key_ratios.p_e_ratio)
print(data.key_ratios.roe)
print(data.shareholding_keys.promoter)
```
