"""Listen for live order, trade and portfolio updates over the order-update websocket.

Type: streaming
Needs: UAT login (PHONE_NO / MPIN in .env); an order placed/modified/cancelled elsewhere while it runs.
Expect: "[OrderUpdate]" / "[TradeUpdate]" lines (prices in rupees) for your own orders; stops after 20 seconds.
Note: on UAT the connect step may fail (UAT /userinfo returns an empty order-service URL); this is an environment issue.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.ticker import orderupdate

# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

events = {"n": 0}

def rupees(paise):
    """Prices arrive as integer paise; show rupees. Missing values print as '-'."""
    return "-" if paise is None else f"{paise / 100:,.2f}"

def on_order_update(msg):
    order = getattr(msg, "intent_order_response", None)
    if order:
        events["n"] += 1
        print("[OrderUpdate]", getattr(order, "intent_order_id", "?"), getattr(order, "order_status", "?"),
              "| mode", getattr(order, "execution_mode", "-"),
              "| entry price", rupees(getattr(order, "entry_price", None)))
        reason = getattr(order, "rejection_msg", None)
        if reason:
            print("  rejected:", reason)

def on_trade_update(msg):
    order = getattr(msg, "intent_order_response", None)
    fill = getattr(order, "trade_fill", None) if order else None
    if fill:
        events["n"] += 1
        print("[TradeUpdate]", getattr(fill, "ref_id", "?"), "qty", getattr(fill, "trade_qty", "-"),
              "price", rupees(getattr(fill, "trade_price", None)))

def on_portfolio_update(msg):
    # Portfolio updates can be frequent, so this is muted by default.
    # print("[PortfolioUpdate]", msg)
    pass

def on_connect(msg):
    print("[status]", msg)

def on_close(reason):
    print("[closed]", reason)

def on_error(err):
    print("[error]", err)

socket = orderupdate.OrderUpdate(
    client=nubra,
    on_order_update=on_order_update,
    on_trade_update=on_trade_update,
    on_portfolio_update=on_portfolio_update,
    on_connect=on_connect,
    on_close=on_close,
    on_error=on_error,
)

socket.connect()

# Listen for a short bounded time, then close (use socket.keep_running() to block forever instead).
time.sleep(20)
socket.close()

if events["n"] == 0:
    print("No order/trade updates received - nothing was placed or changed during the window.")
else:
    print(f"Done: {events['n']} updates received.")
