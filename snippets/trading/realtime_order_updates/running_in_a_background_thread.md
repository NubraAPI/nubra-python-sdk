# Snippet: Running In A Background Thread

Original source path: `trading/realtime_order_updates/running_in_a_background_thread.py`

```python
import threading

def run_socket():
    socket.connect("V2")
    socket.keep_running()

thread = threading.Thread(target=run_socket, daemon=True)
thread.start()
```
