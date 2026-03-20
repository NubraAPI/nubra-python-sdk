from nubra_python_sdk.ticker import orderupdate
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

def on_order_update(msg):
    print("[OrderUpdate]", msg)

def on_trade_update(msg):
    print("[TradeUpdate]", msg)

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
    on_connect=on_connect,
    on_close=on_close,
    on_error=on_error,
)

socket.connect("V2")
socket.keep_running()
