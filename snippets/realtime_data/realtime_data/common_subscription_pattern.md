# Snippet: Common Subscription Pattern

Original source path: `realtime_data/realtime_data/common_subscription_pattern.py`

Resolve `ref_id` values through the instruments master or an option-chain snapshot before subscribing to `orderbook` or `greeks`.

```python
# Index subscriptions use symbols plus exchange.
socket.subscribe(["NIFTY"], data_type="index", exchange="NSE")
socket.subscribe(["SENSEX"], data_type="index", exchange="BSE")
socket.subscribe(["FUT_CRUDEOIL_20260618"], data_type="index", exchange="MCX")

# Option-chain subscriptions use ASSET:EXPIRY (YYYYMMDD) plus exchange.
socket.subscribe(["NIFTY:20260618"], data_type="option", exchange="NSE")
socket.subscribe(["SENSEX:20260618"], data_type="option", exchange="BSE")
socket.subscribe(["CRUDEOIL:20260618"], data_type="option", exchange="MCX")

# Orderbook and Greeks subscriptions use ref_id values (as strings) from the matching exchange.
socket.subscribe([str(nse_ref_id)], data_type="orderbook")
socket.subscribe([str(nse_option_ref_id)], data_type="greeks")

# OHLCV subscriptions use symbols, an interval, and exchange.
socket.subscribe(["NIFTY"], data_type="ohlcv", interval="5m", exchange="NSE")
socket.subscribe(["SENSEX"], data_type="ohlcv", interval="5m", exchange="BSE")
socket.subscribe(["FUT_CRUDEOIL_20260618"], data_type="ohlcv", interval="5m", exchange="MCX")
```
