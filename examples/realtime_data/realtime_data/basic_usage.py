from nubra_python_sdk.ticker import websocketdata
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

def on_market_data(msg):
    print("[MarketData]", msg)

def on_connect(msg):
    print("[status]", msg)

def on_close(reason):
    print("Closed:", reason)

def on_error(err):
    print("Error:", err)

socket = websocketdata.NubraDataSocket(
    client=nubra,
    on_market_data=on_market_data,
    on_connect=on_connect,
    on_close=on_close,
    on_error=on_error,
)

socket.connect()
socket.subscribe(["NIFTY", "HDFCBANK"], data_type="index", exchange="NSE")
socket.keep_running()
