# Snippet: Accessing Data

Original source path: `trading/get_order/accessing_data.py`

```python
# First order
print(result.root[0].order_id)
print(result.root[0].order_status)
print(result.root[0].order_price)
print(result.root[0].avg_filled_price)
print(result.root[0].last_traded_price)
print(result.root[0].display_name)
print(result.root[0].exchange_order_id)
print(result.root[0].ref_id)

# Second order
print(result.root[1].order_id)
print(result.root[1].order_status)
print(result.root[1].order_price)
print(result.root[1].avg_filled_price)
print(result.root[1].last_traded_price)
print(result.root[1].display_name)
print(result.root[1].exchange_order_id)
print(result.root[1].ref_data.ref_id)
```
