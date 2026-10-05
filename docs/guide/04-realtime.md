# 4. Realtime Data

Stream live index values, option chains, market depth, Greeks and candles over a websocket, and turn them into small tools.

[Home](README.md) | [← Previous: Market Data](03-market-data.md) | [Next: Trading →](05-trading.md)

## In this guide

- The websocket callback model: connect, subscribe, receive typed objects, unsubscribe, close.
- Which identifier each stream needs (symbols or `ref_id`) and what each subscription costs.
- Recipes: ATM straddle monitor, multi-index ticker, CSV candle recorder, Greeks alert watcher, depth imbalance.
- Listening for your own order and trade updates, and why that example does not currently connect on UAT.

## You need

- A working setup and login: [Setup](00-setup.md), [Authentication](01-authentication.md). Scripts read `PHONE_NO` / `MPIN` from `.env` and default to UAT (switch to `NubraEnv.PROD` for production).
- Market hours. Streams only tick while the market is open; otherwise scripts end with `No data received - market closed?`.
- Every script is bounded: it streams for 20-25 seconds, cleans up and exits.

## Concepts

### The callback model

Create one `NubraDataSocket`, pass callbacks, call `connect()`, then `subscribe(...)`. The SDK calls your function for each message. Use one central receiver (`on_market_data`) or a callback per stream. Imports and a minimal constructor (from [index_data/basic_usage.py](../../examples/realtime_data/index_data/basic_usage.py)):

```python
from nubra_python_sdk.ticker import websocketdata
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

socket = websocketdata.NubraDataSocket(
    client=nubra,
    on_index_data=on_index_data,
    on_connect=on_connect,
    on_close=on_close,
    on_error=on_error,
)
```

All the callbacks you can pass:

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

### Subscribe, unsubscribe, close

Connect first, subscribe, run, then unsubscribe (frees session weight) and close:

```python
socket.connect()
socket.subscribe(["NIFTY"], data_type="index", exchange="NSE")
time.sleep(20)                       # or socket.keep_running() to block forever
socket.unsubscribe(["NIFTY"], data_type="index", exchange="NSE")
socket.close()
```

The examples use `time.sleep(N)` so they end on their own. For a long-lived bot, call `socket.keep_running()` instead; it blocks until you stop the process.

### What each stream subscribes with

| Stream (`data_type`) | Identifier | Example |
|---|---|---|
| `index` | symbols + `exchange` | `["NIFTY"]`, `exchange="NSE"` |
| `option` | `ASSET:EXPIRY` (YYYYMMDD) + `exchange` | `["NIFTY:20260618"]` |
| `orderbook` | `ref_id` as a string | `[str(ref_id)]` |
| `greeks` | `ref_id` as a string | `[str(option_ref_id)]` |
| `ohlcv` | symbols + `interval` + `exchange` | `["NIFTY"]`, `interval="5m"` |

The index stream also carries stocks (for example HDFCBANK). Use it for LTP ticks of either.

Get `ref_id` values from the instruments master ([Instruments](02-instruments.md)) or an option-chain snapshot. OHLCV intervals: `1s, 2s, 5s, 1m, 2m, 3m, 5m, 10m, 15m, 30m, 1h, 2h, 4h, 1d`.

### Subscription weights

Each session has a budget of 50,000. Cost per subscribed instrument or key:

| Stream | Weight |
|---|---|
| Option chain | 20 |
| Order book | 5 |
| OHLCV | 2 |
| Index | 1 |
| Greeks | 1 |

Trading and historical API limits are in [schemas/api_rate_limits.md](../../schemas/api_rate_limits.md).

Example: 300 option-chain + 400 order-book + 1,000 index = 6,000 + 2,000 + 1,000 = 9,000 / 50,000. 2,600 option-chain subscriptions = 52,000, which exceeds the limit and is not allowed.

### Typed objects and paise

Callbacks receive typed objects, not raw JSON. The examples read fields with `getattr(msg, "...", None)` so a missing field never crashes the callback. Prices arrive as integer paise; the examples divide by 100 and print rupees.

## The examples, in order

All outputs are real UAT runs, trimmed. "Unclosed client session" style warnings are omitted.

### 1. Central receiver: [realtime_data/basic_usage.py](../../examples/realtime_data/realtime_data/basic_usage.py)

One `on_market_data` callback receives every stream type. Useful when you want to route messages yourself.

```python
def on_market_data(msg):
    ticks["n"] += 1
    # One central receiver gets every stream type; index ticks carry these fields.
    print("[MarketData]", getattr(msg, "indexname", None) or type(msg).__name__,
          rupees(getattr(msg, "index_value", None)),
          f"{getattr(msg, 'changepercent', None) or 0:+.2f}%")
```

Run: `py -3.12 examples/realtime_data/realtime_data/basic_usage.py`

Real output:

```text
[status] WebSocket Connected!
[MarketData] SENSEX 72,013.47 +0.14%
[MarketData] HDFCBANK 707.55 -1.89%
[MarketData] NIFTY 22,458.50 +0.16%
[MarketData] SENSEX 72,012.66 +0.14%
[MarketData] HDFCBANK 707.90 -1.84%
[MarketData] NIFTY 22,458.10 +0.16%
[MarketData] SENSEX 72,012.83 +0.14%
```

### 2. Index data: [index_data/basic_usage.py](../../examples/realtime_data/index_data/basic_usage.py)

Live index and stock values with day high, low and percent change, across two exchanges on one socket. A live watchlist feed.

```python
socket.subscribe(["NIFTY", "HDFCBANK"], data_type="index", exchange="NSE")
socket.subscribe(["SENSEX"], data_type="index", exchange="BSE")
```

Run: `py -3.12 examples/realtime_data/index_data/basic_usage.py`

Real output:

```text
[status] WebSocket Connected!
[INDEX] SENSEX value 71,989.46 high 72,631.10 low 71,294.49 chg +0.11%
[INDEX] HDFCBANK value 706.40 high 734.20 low 701.25 chg -2.05%
[INDEX] NIFTY value 22,449.30 high 22,621.80 low 22,217.65 chg +0.12%
[INDEX] NIFTY value 22,449.60 high 22,621.80 low 22,217.65 chg +0.12%
[INDEX] SENSEX value 71,987.49 high 72,631.10 low 71,294.49 chg +0.11%
[INDEX] HDFCBANK value 706.40 high 734.20 low 701.25 chg -2.05%
```

#### Recipe: [index_data/multi_index_ticker.py](../../examples/realtime_data/index_data/multi_index_ticker.py)

Keeps the latest value per index in a dict and prints a table every 5 seconds instead of every tick. Pattern: callbacks store state, the main loop displays it.

```python
latest[name] = (value if value is not None else prev_value, chg if chg is not None else prev_chg)
```

Run: `py -3.12 examples/realtime_data/index_data/multi_index_ticker.py`

Real output:

```text
[status] WebSocket Connected!
INDEX                VALUE    CHG %
NIFTY            22,448.40    +0.12
BANKNIFTY        54,603.30    +0.28
FINNIFTY         24,609.15    +0.22
SENSEX           71,979.87    +0.10

INDEX                VALUE    CHG %
NIFTY            22,449.50    +0.12
```

### 3. Option chain: [option_chain_data/basic_usage.py](../../examples/realtime_data/option_chain_data/basic_usage.py)

Streams the whole chain for one expiry. The expiry comes from a snapshot (`YYYYMMDD`) rather than being hard-coded; each update carries all strikes plus the ATM strike. Option-chain subscriptions are the most expensive (weight 20).

```python
expiry = market_data.option_chain("NIFTY", exchange="NSE").chain.expiry
key = f"NIFTY:{expiry}"
...
socket.subscribe([key], data_type="option", exchange="NSE")
```

Run: `py -3.12 examples/realtime_data/option_chain_data/basic_usage.py`

Real output:

```text
[status] WebSocket Connected!
[OPTION] 20261006 spot 22,446.75 ATM 22,450.00 CE/PE count 91/91 ATM CE 111.20 ATM PE 93.60
[OPTION] 20261006 spot 22,447.40 ATM 22,450.00 CE/PE count 91/91 ATM CE 113.15 ATM PE 91.50
[OPTION] 20261006 spot 22,447.40 ATM 22,450.00 CE/PE count 91/91 ATM CE 113.15 ATM PE 91.50
[OPTION] 20261006 spot 22,447.70 ATM 22,450.00 CE/PE count 91/91 ATM CE 114.50 ATM PE 90.45
```

#### Recipe: [option_chain_data/atm_straddle_monitor.py](../../examples/realtime_data/option_chain_data/atm_straddle_monitor.py)

Adds ATM call and put LTPs into a live straddle price, about one line per second, with a low/high summary at the end. Shows how much premium the market is charging for movement.

```python
straddle = ce_ltp + pe_ltp
state["values"].append(straddle)
now = time.time()
if now - state["last_print"] >= 1:  # throttle to ~1 line per second
```

Run: `py -3.12 examples/realtime_data/option_chain_data/atm_straddle_monitor.py`

Real output:

```text
[status] WebSocket Connected!
spot 22,449.40 | ATM 22,450.00 | CE 115.10 + PE 89.80 = straddle 204.90
spot 22,449.00 | ATM 22,450.00 | CE 114.90 + PE 90.15 = straddle 205.05
spot 22,448.75 | ATM 22,450.00 | CE 114.60 + PE 89.95 = straddle 204.55
spot 22,448.95 | ATM 22,450.00 | CE 114.60 + PE 90.20 = straddle 204.80
...
Straddle range over the window: low 204.25 / high 205.05
```

### 4. Order book (market depth): [order_book_data/basic_usage.py](../../examples/realtime_data/order_book_data/basic_usage.py)

Order book needs a string `ref_id`. The script looks up HDFCBANK in the instruments master, then prints LTP with best bid and ask and their quantities.

```python
instrument = instruments.get_instrument_by_symbol("HDFCBANK", exchange="NSE")
ref_id = instrument.ref_id
...
socket.subscribe([str(ref_id)], data_type="orderbook")
```

Run: `py -3.12 examples/realtime_data/order_book_data/basic_usage.py`

Real output:

```text
[status] WebSocket Connected!
[ORDERBOOK] LTP 706.65 | bid 706.45 x 16 | ask 706.55 x 1926
[ORDERBOOK] LTP 706.45 | bid 706.45 x 91 | ask 706.55 x 1584
[ORDERBOOK] LTP 706.55 | bid 706.40 x 824 | ask 706.45 x 118
[ORDERBOOK] LTP 706.55 | bid 706.50 x 67 | ask 706.55 x 1004
```

#### Recipe: [order_book_data/depth_imbalance.py](../../examples/realtime_data/order_book_data/depth_imbalance.py)

Sums bid and ask quantity across all levels and reports an imbalance from -100 to +100 (positive means more resting buyers). A quick read on short-term pressure, not a signal on its own.

```python
imbalance = 100 * (bid_qty - ask_qty) / total
```

Run: `py -3.12 examples/realtime_data/order_book_data/depth_imbalance.py`

Real output:

```text
[status] WebSocket Connected!
bid 706.70 | ask 706.80 | bid qty 16168 | ask qty 11782 | imbalance +16
bid 706.70 | ask 706.75 | bid qty 17559 | ask qty 8564 | imbalance +34
bid 706.55 | ask 706.75 | bid qty 30985 | ask qty 15692 | imbalance +33
bid 706.50 | ask 706.60 | bid qty 34921 | ask qty 10023 | imbalance +55
```

### 5. Greeks: [greeks_data/basic_usage.py](../../examples/realtime_data/greeks_data/basic_usage.py)

Live LTP, IV, delta, gamma, theta and vega for one option: the ATM call, picked from a snapshot chain. Greeks also subscribe by string `ref_id`.

```python
atm_ce = next(
    (opt for opt in chain.ce if opt.strike_price == chain.at_the_money_strike),
    chain.ce[0],
)
ref_id = str(atm_ce.ref_id)
```

Run: `py -3.12 examples/realtime_data/greeks_data/basic_usage.py`

Real output:

```text
[status] WebSocket Connected!
[GREEKS] LTP 115.95 IV 0.2030 delta 0.5459 gamma 0.0016 theta -66.5712 vega 4.9498
[GREEKS] LTP 115.30 IV 0.2038 delta 0.5402 gamma 0.0016 theta -66.9297 vega 4.9565
[GREEKS] LTP 114.50 IV 0.2038 delta 0.5402 gamma 0.0016 theta -66.9297 vega 4.9565
[GREEKS] LTP 114.60 IV 0.2046 delta 0.5421 gamma 0.0016 theta -66.5177 vega 4.9543
```

#### Recipe: [greeks_data/greeks_alert_watch.py](../../examples/realtime_data/greeks_data/greeks_alert_watch.py)

Watches both ATM legs and prints an `ALERT` line when IV moves 1% or premium moves 2% (relative) from the last reference reading, then re-arms from the new level.

```python
IV_MOVE_ALERT = 0.01       # alert if IV moves 1% (relative) from the reference reading
PREMIUM_MOVE_ALERT = 0.02  # alert if LTP moves 2% (relative) from the reference reading
```

Run: `py -3.12 examples/realtime_data/greeks_data/greeks_alert_watch.py`

Real output (no threshold was crossed in this window, so no ALERT lines):

```text
[status] WebSocket Connected!
[CE] LTP 114.10 | IV 0.20426489412784576 | delta 0.540
[PE] LTP 90.15 | IV 0.20418860018253326 | delta -0.460
[CE] LTP 114.55 | IV 0.2023577243089676 | delta 0.543
[PE] LTP 89.95 | IV 0.2053328901529312 | delta -0.457
```

### 6. OHLCV candles: [ohlcv_data/basic_usage.py](../../examples/realtime_data/ohlcv_data/basic_usage.py)

Live 1-minute candles. Each message updates the current candle (open, high, low, close, volume), so you see the same candle evolve.

```python
socket.subscribe(["NIFTY", "HDFCBANK"], data_type="ohlcv", interval="1m", exchange="NSE")
```

Run: `py -3.12 examples/realtime_data/ohlcv_data/basic_usage.py`

Real output:

```text
[status] WebSocket Connected!
[OHLCV] HDFCBANK O 706.35 H 706.35 L 706.20 C 706.30 vol 26273
[OHLCV] NIFTY O 22,451.05 H 22,455.55 L 22,450.80 C 22,452.80 vol 274137
[OHLCV] SENSEX O 71,981.20 H 71,997.05 L 71,981.20 C 71,996.38 vol 21759
[OHLCV] NIFTY O 22,451.05 H 22,455.55 L 22,450.80 C 22,451.90 vol 295124
```

#### Recipe: [ohlcv_data/ohlcv_to_csv.py](../../examples/realtime_data/ohlcv_data/ohlcv_to_csv.py)

Records NIFTY candle updates to `output/ohlcv_NIFTY_1m.csv` (IST time, prices in rupees). A starting point for your own intraday dataset. The folder README mentions 1-second candles, but the script subscribes to `1m` because the 1s interval delivered nothing on UAT.

```python
socket.subscribe([SYMBOL], data_type="ohlcv", interval="1m", exchange="NSE")
```

Run: `py -3.12 examples/realtime_data/ohlcv_data/ohlcv_to_csv.py`

Real output:

```text
[status] WebSocket Connected!
Closed: WebSocket closed
Wrote 26 rows to <repo>\examples\realtime_data\ohlcv_data\output\ohlcv_NIFTY_1m.csv
```

The same run also logged `Error: Cannot send subscription: WebSocket is not connected` near the end, around the unsubscribe step; the rows were still written.

### 7. Realtime order updates: [trading/realtime_order_updates/basic_usage.py](../../examples/trading/realtime_order_updates/basic_usage.py)

A separate socket, `orderupdate.OrderUpdate`, pushes updates for your own orders, trades and portfolio while you place, modify or cancel orders elsewhere (see [Trading](05-trading.md)).

```python
socket = orderupdate.OrderUpdate(
    client=nubra,
    on_order_update=on_order_update,
    on_trade_update=on_trade_update,
    on_portfolio_update=on_portfolio_update,
    on_connect=on_connect,
    on_close=on_close,
    on_error=on_error,
)
```

Run: `py -3.12 examples/trading/realtime_order_updates/basic_usage.py`

**Status: not verifiable on UAT.** The docs describe it as working on PROD, but on UAT the connection currently fails. The UAT `/userinfo` response returns an empty `order_service_ws_url`, which overwrites the SDK's default URL. This is an SDK/backend bug, not an error in your code. Real UAT output:

```text
[error] Connection failed: ?token=<redacted>
[closed] WebSocket closed
[error] Connection failed: ?token=<redacted>
[closed] WebSocket closed
...
No order/trade updates received - nothing was placed or changed during the window.
```

Optional UAT workaround: the default URL `wss://uatapi.nubra.io/oms-socket-latest/ws` works when set manually. Put this right after `InitNubraSdk`:

```python
nubra.WEBSOCKET_URL_OMS = "wss://uatapi.nubra.io/oms-socket-latest/ws"
```

We did not capture a successful order-update session on UAT, so treat the workaround and the PROD behaviour as unverified here. Skip the line on PROD.

## Go further

1. In `index_data/basic_usage.py`, add `BANKNIFTY` and `FINNIFTY` and print only ticks that move more than 0.1% from the previous value.
2. Extend `atm_straddle_monitor.py` to record the opening straddle and print the change at the end.
3. Run `ohlcv_to_csv.py` with `interval="5m"` and compare the CSV with the historical candles from [Market Data](03-market-data.md).
4. Add a delta alert to `greeks_alert_watch.py`, and total your subscriptions' weight against the 50,000 limit.

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `No data received - market closed?` | Script ran outside market hours; no ticks arrived. | Run during market hours. |
| 1s OHLCV interval delivers nothing | On UAT, `interval="1s"` delivered no candles while `1m` worked. | Use `1m` (or another interval) on UAT. |
| No data for `orderbook` or `greeks` | These streams need a `ref_id` as a string, not a symbol. | Look it up from the instruments master or an option-chain snapshot and pass `[str(ref_id)]`. |
| Order updates: `Connection failed: ?token=...` on UAT | UAT `/userinfo` returns an empty `order_service_ws_url` that overwrites the SDK default (SDK/backend bug). | Optionally set `nubra.WEBSOCKET_URL_OMS = "wss://uatapi.nubra.io/oms-socket-latest/ws"` right after `InitNubraSdk`. Works on PROD per the docs; not verifiable on UAT. |
| `Cannot send subscription: WebSocket is not connected` | A subscribe/unsubscribe was sent while the socket was not connected (before `connect()` completed, or after it dropped). | Call `connect()` and wait for `WebSocket Connected!` before subscribing; unsubscribe only while still connected. |

## Summary

One `NubraDataSocket`: callbacks in, `connect()`, `subscribe()`, run, `unsubscribe()`, `close()`. Index and OHLCV use symbols, option chain uses `ASSET:EXPIRY`, order book and Greeks use string `ref_id`; stay under the 50,000 weight budget and remember prices are in paise. Order updates use a separate socket that could not be verified on UAT.

[Home](README.md) | [← Previous: Market Data](03-market-data.md) | [Next: Trading →](05-trading.md)
