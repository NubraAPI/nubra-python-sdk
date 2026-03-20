# Snippet: Accessing Data

Original source path: `portfolio/funds/accessing_data.py`

```python
pfm = result.port_funds_and_margin

print(pfm.client_code)
print(pfm.start_of_day_funds)
print(pfm.net_trading_amount)
print(pfm.net_withdrawal_amount)
print(pfm.total_collateral)
print(pfm.net_margin_available)
print(pfm.total_margin_blocked)
print(pfm.derivative_margin_blocked)
print(pfm.brokerage)
```
