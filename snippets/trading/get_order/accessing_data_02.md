# Snippet: Accessing Data 02

Original source path: `trading/get_order/accessing_data_02.py`

```python
print(result.order_id)
print(result.ref_id)
print(result.order_status)
print(result.avg_filled_price)
print(result.order_price)
print(result.LTP)
print(result.exchange)
print(result.price_type)
print(result.validity_type)

if result.ref_data:
    print(result.ref_data.ref_id)
    print(result.ref_data.asset)
    print(result.ref_data.nubra_name)

if result.algo_params:
    print(result.algo_params.trigger_price)
```
