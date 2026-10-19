"""Run a market-data stream and an order-update stream together in one process, each reconnecting on its own.

Type: streaming
Needs: UAT login (PHONE_NO / MPIN in .env); market hours for ticks; an order placed elsewhere to see order events.
Expect: "[INDEX]" lines for NIFTY and "[OrderUpdate]" / "[TradeUpdate]" lines for your own orders;
        stops after 25 seconds and prints a count for each stream.
Note: on UAT the order-update connect step may fail (UAT /userinfo returns an empty order-service URL); the
      market-data stream keeps running either way, which is the point of keeping the two sockets independent.
Tested with: nubra-sdk 0.5.4 (UAT)

Both socket classes reconnect with exponential backoff on their own (`reconnect=True`, the default) and the
data socket re-subscribes after a reconnect, so no hand-written retry loop is needed. A dropped market-data
connection does not touch the order-update connection because they are separate sockets with separate callbacks.
"""
import time

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.ticker import orderupdate, websocketdata

RUN_SECONDS = 25

# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

counts = {"index": 0, "orders": 0}


def rupees(paise):
    """Prices arrive as integer paise; show rupees. Missing values print as '-'."""
    return "-" if paise is None else f"{paise / 100:,.2f}"


# --- market data stream ---
def on_index_data(msg):
    counts["index"] += 1
    print("[INDEX]", getattr(msg, "indexname", "?"), "value", rupees(getattr(msg, "index_value", None)))


def on_data_status(msg):
    print("[market data]", msg)


# --- order update stream ---
def on_order_update(msg):
    order = getattr(msg, "intent_order_response", None)
    if order:
        counts["orders"] += 1
        print("[OrderUpdate]", getattr(order, "intent_order_id", "?"), getattr(order, "order_status", "?"))


def on_trade_update(msg):
    order = getattr(msg, "intent_order_response", None)
    fill = getattr(order, "trade_fill", None) if order else None
    if fill:
        counts["orders"] += 1
        print("[TradeUpdate]", getattr(fill, "ref_id", "?"), "qty", getattr(fill, "trade_qty", "-"),
              "price", rupees(getattr(fill, "trade_price", None)))


def on_order_status(msg):
    print("[order updates]", msg)


data_socket = websocketdata.NubraDataSocket(
    client=nubra,
    on_index_data=on_index_data,
    on_connect=on_data_status,
    on_close=lambda reason: print("[market data] closed:", reason),
    on_error=lambda err: print("[market data] error:", err),
)
order_socket = orderupdate.OrderUpdate(
    client=nubra,
    on_order_update=on_order_update,
    on_trade_update=on_trade_update,
    on_portfolio_update=lambda msg: None,  # frequent; muted
    on_connect=on_order_status,
    on_close=lambda reason: print("[order updates] closed:", reason),
    on_error=lambda err: print("[order updates] error:", err),
)

data_socket.connect()
order_socket.connect()
data_socket.subscribe(["NIFTY"], data_type="index", exchange="NSE")

# Run for a short bounded time, then close both (use keep_running() on each to block forever instead).
time.sleep(RUN_SECONDS)
data_socket.close()
order_socket.close()

print(f"Done: {counts['index']} index ticks, {counts['orders']} order/trade events.")
if counts["index"] == 0:
    print("No index ticks received - market closed?")
