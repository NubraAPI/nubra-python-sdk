# Snippet: Instruments Master

Original source path: `get_instruments/instruments_master.py`

```python
# NSE instruments (default)
instruments_df = instruments.get_instruments_dataframe()

# BSE instruments (explicit)
instruments_df = instruments.get_instruments_dataframe(exchange="BSE")
```
