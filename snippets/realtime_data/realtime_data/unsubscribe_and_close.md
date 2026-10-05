# Snippet: Unsubscribe And Close

```python
socket.connect()
socket.subscribe(["NIFTY"], data_type="index", exchange="NSE")
time.sleep(20)                       # or socket.keep_running() to block forever
socket.unsubscribe(["NIFTY"], data_type="index", exchange="NSE")   # frees session weight
socket.close()
```
