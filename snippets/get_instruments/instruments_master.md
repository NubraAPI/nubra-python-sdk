# Snippet: Instruments Master

Original source path: `get_instruments/instruments_master.py`

```python
# NSE instruments (default when exchange is omitted)
instruments_df = instruments.get_instruments_dataframe(exchange="NSE")

# BSE instruments (explicit)
instruments_df = instruments.get_instruments_dataframe(exchange="BSE")

# MCX instruments (explicit)
instruments_df = instruments.get_instruments_dataframe(exchange="MCX")
```
