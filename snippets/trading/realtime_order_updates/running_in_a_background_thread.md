# Snippet: Running In A Background Thread

Original source path: `trading/realtime_order_updates/running_in_a_background_thread.py`

```python
import threading

def run_socket():
    socket.connect()
    socket.keep_running()

thread = threading.Thread(target=run_socket, daemon=True)
thread.start()

# ... do other work, then stop the stream
socket.close()
```
