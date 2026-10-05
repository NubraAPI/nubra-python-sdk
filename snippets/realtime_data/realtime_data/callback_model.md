# Snippet: Callback Model

```python
socket = websocketdata.NubraDataSocket(
    client=nubra,
    on_market_data=on_market_data,    # one central receiver for every stream
    on_index_data=on_index_data,      # or dedicated per-stream callbacks:
    on_option_data=on_option_data,
    on_orderbook_data=on_orderbook_data,
    on_greeks_data=on_greeks_data,
    on_ohlcv_data=on_ohlcv_data,
    on_connect=on_connect,            # on_connect(msg: str)
    on_close=on_close,                # on_close(reason: str)
    on_error=on_error,                # on_error(err: str)
)
```
