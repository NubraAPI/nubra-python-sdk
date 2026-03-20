# Snippet: Common Subscription Pattern

Original source path: `realtime_data/realtime_data/common_subscription_pattern.py`

```python
socket.subscribe(["NIFTY"], data_type="index", exchange="NSE")
socket.subscribe(["RELIANCE:20250626"], data_type="option", exchange="NSE")
socket.subscribe(["1746686"], data_type="orderbook")
socket.subscribe(["1058227"], data_type="greeks", exchange="NSE")
socket.subscribe(["NIFTY"], data_type="ohlcv", interval="5m", exchange="NSE")
```
