# 5. Trading

Place, price, modify, cancel and read orders with `NubraTrader`, from a one-share limit order to multi-leg NIFTY strategies.

[Home](README.md) | [← Previous: Realtime Data](04-realtime.md) | [Next: Portfolio →](06-portfolio.md)

## In this guide

- Build a V3 order payload and know what each key does.
- Place single, multi and strategy (multi-leg) orders, with stop-loss, target, trailing stop-loss, iceberg, GTE and timed entry/exit.
- Check margin before placing, and refuse to place when funds are short.
- Modify and cancel orders (including a stop-loss only) without hitting the post-modify cancel lock.
- Read orders by id, tag, status and bucket, and watch status changes by polling.
- Use the workflow scripts: margin guard, status tracker, bracket order, square-off, cleanup.

## You need

- A working login. See [00-setup.md](00-setup.md).
- Run everything on UAT first. Every script defaults to `NubraEnv.UAT`.
- **Mutating examples place real orders in whichever environment you are on.** Read a script before switching it to `NubraEnv.PROD`. `square_off_all_positions.py` closes every open position and `cancel_all_open_orders.py` cancels every open order on the account.
- Most scripts need the market open (they read a live LTP or option chain).

## Concepts

### The V3 order payload

One dict goes to `trader.create_order(...)`. Pass a list of dicts to place several independent orders in one request.

| Key | Meaning |
| --- | --- |
| `refId` | Instrument id from `get_instrument_by_symbol(...).ref_id`. Omitted for strategy orders (legs carry their own). |
| `qty` | Quantity. For a strategy, the lot size (one strategy unit). |
| `side` | `BUY` or `SELL`. Strategy orders are always `BUY`. |
| `deliveryType` | `IDAY` (intraday) or `CNC` (delivery; used for strategies and future-dated GTE). |
| `priceType` | `LIMIT` or `MARKET`. |
| `validityType` | `DAY`, `IOC` (market orders), or `GTE` (good till expiry, needs `goodTillDate`). |
| `executionMode` | `ENTRY` (entry only) or `ENTRY_AND_EXIT` (entry plus an `exitConfig`). |
| `entryPrice` | Limit price, or signed net premium for a strategy. Omit for `MARKET`. |
| `entryConfig` | `triggers.ltp.atOrAbove.value` (trigger entry) or `entryTime` (timed entry). |
| `exitConfig` | `stoplossParams`, `targetParams`, or `exitTime`. |
| `icebergInfo` | `maxQtyPerLeg` or `numberOfLegs` (one of them, not both). |
| `stratTags` | A list with exactly one tag. Hyphens only (no spaces or underscores). |
| `isMultiLeg` | `False` for single orders, `True` for strategies. |

Stop-loss and target prices are wrapped as `{"value": paise}`:

| Block | Keys |
| --- | --- |
| `stoplossParams` | `stoplossTriggerPrice`, `stoplossLimitPrice`, optional `stoplossTrailJump` |
| `targetParams` | `targetProfitTriggerPrice`, `targetProfitLimitPrice` |

The stop-loss limit price must be less than or equal to the stop-loss trigger price (for a BUY entry).

### Prices are integer paise

Every price in a request or response is an integer in paise, snapped to the instrument's `tick_size` (also in paise). Every example uses the same helper:

```python
def to_tick(price):
    return int(round(price / tick_size) * tick_size)
```

Scripts divide by 100 only when printing.

### Strategy (flexi) orders

- `side` is always `"BUY"`. Direction per leg comes from the sign of `legs[].unitQty` (`1` long, `-1` short).
- `entryPrice` is the signed net premium in paise. A net credit is negative.
- A strategy has one strategy-level order id; legs have no ids of their own.
- With `GTE`, `goodTillDate` must not be after the option expiry, and `exitConfig.exitTime` must not be sent together with `GTE`.

### Order lifecycle

| Stage | What to expect |
| --- | --- |
| Create | `create_order` returns `result.orders` with an `intentOrderId`. |
| Reach the book | About 1-2 seconds. `get_order` straight after create can return nothing. |
| Working | `OPEN` (or `GTE` for good-till-expiry). |
| Final | `EXECUTED`, `CANCELLED`, `REJECTED` or `EXPIRED`. |
| After a modify | Wait about 5 seconds before cancelling. |

`modify_orders_sentinel` and `cancel_orders_sentinel` return only an acknowledgement (`{'message': 'order modify request pushed successfully'}`). Fetch the order to see its real state.

## The examples, in order

All paths below are under `examples/trading/`.

### Setup

| File | What it does |
| --- | --- |
| [overview/basic_usage.py](../../examples/trading/overview/basic_usage.py) | Logs in and builds `NubraTrader`. Places nothing. |

```python
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra)
```

Real output:

```
Logged in. NubraTrader is ready (UAT).
```

Realtime order updates over websocket are covered in [Realtime Data](04-realtime.md); the script is [realtime_order_updates/basic_usage.py](../../examples/trading/realtime_order_updates/basic_usage.py).

### Single orders (`place_order/`)

Start with [basic_usage.py](../../examples/trading/place_order/basic_usage.py): look up ICICIBANK, read the LTP, place a 1-share limit order at LTP, then cancel it with retries. Every pattern below shares that skeleton and changes only the payload.

| File | What it does |
| --- | --- |
| [basic_usage.py](../../examples/trading/place_order/basic_usage.py) | 1-share limit order at LTP, then cleanup cancel. |
| [example_order_patterns.py](../../examples/trading/place_order/example_order_patterns.py) | Plain limit order (`ENTRY`). |
| [example_order_patterns_02.py](../../examples/trading/place_order/example_order_patterns_02.py) | Trigger entry (LTP at or above) with a stop-loss exit. |
| [example_order_patterns_03.py](../../examples/trading/place_order/example_order_patterns_03.py) | Iceberg, 20 shares at 10 per leg (`maxQtyPerLeg`). |
| [example_order_patterns_04.py](../../examples/trading/place_order/example_order_patterns_04.py) | Market order (`MARKET` + `IOC`, no price). Fills and opens a position; not cancelled. |
| [example_order_patterns_05.py](../../examples/trading/place_order/example_order_patterns_05.py) | Iceberg split into a fixed leg count (`numberOfLegs`). |
| [example_order_patterns_06.py](../../examples/trading/place_order/example_order_patterns_06.py) | Limit order with a trailing stop-loss (`stoplossTrailJump`). |
| [example_order_patterns_07.py](../../examples/trading/place_order/example_order_patterns_07.py) | Limit order with stop-loss and target. |
| [example_order_patterns_08.py](../../examples/trading/place_order/example_order_patterns_08.py) | Good-till-expiry CNC order, 7 days out (`GTE` + `goodTillDate`). |
| [example_order_patterns_09.py](../../examples/trading/place_order/example_order_patterns_09.py) | Timed entry (+5 min) and timed exit (+10 min). |

The core call (from `basic_usage.py`):

```python
result = trader.create_order({
    "refId": instrument.ref_id,
    "qty": 1,
    "side": "BUY",
    "deliveryType": "IDAY",
    "priceType": "LIMIT",
    "validityType": "DAY",
    "isMultiLeg": False,
    "executionMode": "ENTRY",
    "entryPrice": to_tick(ltp),
    "stratTags": ["python-sdk-v3-basic-usage"],  # One tag only, hyphens only.
})
```

Real output:

```
LTP: Rs 1319.30
Order 19175: OPEN, qty=1, price=market
Cancel: {'message': 'order cancellation request pushed successfully'}
```

The `price=market` text is the UAT echo for this limit order; the script prints "market" when the response carries no `entryPrice`. Do not read it as the order type.

Trigger entry plus stop-loss (pattern 02):

```python
    "executionMode": "ENTRY_AND_EXIT",
    "entryPrice": trigger_price,
    "entryConfig": {
        "triggers": {"ltp": {"atOrAbove": {"value": trigger_price}}},
    },
    "exitConfig": {
        "stoplossParams": {
            "stoplossTriggerPrice": {"value": to_tick(ltp * 0.98)},
            "stoplossLimitPrice": {"value": to_tick(ltp * 0.979)},
        },
    },
```

Market order (pattern 04). The only differences from a limit order are the price type and validity, and no `entryPrice`:

```python
    "priceType": "MARKET",
    "validityType": "IOC",
```

Real output:

```
Order 19182: OPEN, qty=1, price=market
```

Good-till-expiry (pattern 08):

```python
good_till = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
...
    "deliveryType": "CNC",
    "validityType": "GTE",
    "goodTillDate": good_till,
```

Real output shows the status `GTE` rather than `OPEN`:

```
LTP: Rs 1318.50
Order 19238: GTE, qty=1, price=market
Cancel: {'message': 'order cancellation request pushed successfully'}
```

Timed entry/exit (pattern 09): `exitTime` must be at least 30 seconds after `entryTime` and inside the market session.

```python
    "entryConfig": {"entryTime": entry_time},
    "exitConfig": {"exitTime": exit_time},
```

### Multi orders (`place_multi_order/`)

Pass a list to `create_order` to send several independent orders in one request. Each item has its own `refId`, tick size and tag. These are not linked legs.

| File | What it does |
| --- | --- |
| [basic_usage.py](../../examples/trading/place_multi_order/basic_usage.py) | BUY ICICIBANK and SELL RELIANCE, both limit. |
| [example_order_patterns.py](../../examples/trading/place_multi_order/example_order_patterns.py) | Same two-limit-order request. |
| [example_order_patterns_02.py](../../examples/trading/place_multi_order/example_order_patterns_02.py) | A plain limit order plus a limit order with a stop-loss exit. |
| [example_order_patterns_03.py](../../examples/trading/place_multi_order/example_order_patterns_03.py) | A limit order plus a market order (the market leg fills). |

```python
result = trader.create_order([
    {"refId": icici.ref_id, ..., "stratTags": ["python-sdk-v3-multi-limit-icici"]},
    {"refId": reliance.ref_id, ..., "stratTags": ["python-sdk-v3-multi-limit-reliance"]},
])
```

Real output:

```
ICICIBANK LTP: Rs 1319.10
RELIANCE LTP: Rs 1177.90
Order 19166: OPEN, qty=1, price=market
Order 19167: OPEN, qty=1, price=market
Cancel: {'message': 'order cancellation request pushed successfully'}
```

### Strategy (flexi) orders (`place_flexi_order/`)

All six patterns build legs from the NIFTY option chain around the ATM strike and send one `isMultiLeg: True` order.

| File | Strategy | Legs (`unitQty`) |
| --- | --- | --- |
| [basic_usage.py](../../examples/trading/place_flexi_order/basic_usage.py) | Long straddle with trigger entry, stop-loss and target | ATM CE +1, ATM PE +1 |
| [example_order_patterns.py](../../examples/trading/place_flexi_order/example_order_patterns.py) | Long straddle | ATM CE +1, ATM PE +1 |
| [example_order_patterns_02.py](../../examples/trading/place_flexi_order/example_order_patterns_02.py) | Long strangle | CE at ATM+2 strikes +1, PE at ATM-2 strikes +1 |
| [example_order_patterns_03.py](../../examples/trading/place_flexi_order/example_order_patterns_03.py) | Iron condor | PE ATM-4 +1, PE ATM-2 -1, CE ATM+2 -1, CE ATM+4 +1 |
| [example_order_patterns_04.py](../../examples/trading/place_flexi_order/example_order_patterns_04.py) | Iron butterfly | PE ATM-2 +1, PE ATM -1, CE ATM -1, CE ATM+2 +1 |
| [example_order_patterns_05.py](../../examples/trading/place_flexi_order/example_order_patterns_05.py) | Bull call spread, `GTE`, trigger entry, trailing stop-loss, target | CE ATM +1, CE ATM+2 -1 |
| [example_order_patterns_06.py](../../examples/trading/place_flexi_order/example_order_patterns_06.py) | Bear call spread (net credit, negative `entryPrice`) | CE ATM -1, CE ATM+2 +1 |

Helpers shared by every script:

```python
def net_price(legs):
    # Strategy entryPrice is the signed net premium in paise (negative for a net credit).
    return to_tick(sum(qty * opt.last_traded_price for opt, qty in legs))


def leg_payload(legs):
    return [{"refId": opt.ref_id, "unitQty": qty} for opt, qty in legs]
```

The order (from `example_order_patterns.py`):

```python
result = trader.create_order({
    "isMultiLeg": True,
    "qty": lot_size,  # one strategy unit
    "side": "BUY",  # strategy side is always BUY; leg direction comes from the sign of unitQty
    "deliveryType": "CNC",
    "priceType": "LIMIT",
    "validityType": "DAY",
    "executionMode": "ENTRY",
    "entryPrice": entry_price,
    "legs": leg_payload(legs),
    "stratTags": ["python-sdk-v3-nifty-buy-straddle"],  # One tag only, hyphens only.
})
```

Pattern 05 keeps `goodTillDate` inside the option expiry:

```python
expiry_day = datetime.strptime(str(chain.expiry), "%Y%m%d").replace(hour=9, tzinfo=timezone.utc)
good_till = min(datetime.now(timezone.utc) + timedelta(days=2), expiry_day).strftime("%Y-%m-%dT%H:%M:%S.000Z")
```

Real output (`basic_usage.py`, then pattern 05 which shows `GTE`):

```
Order 19157: OPEN, qty=65, net premium=market
Cancel: {'message': 'order cancellation request pushed successfully'}

Order 19163: GTE, qty=65, net premium=market
Cancel: {'message': 'order cancellation request pushed successfully'}
```

Quantity 65 is the NIFTY lot size seen on UAT in these runs.

### Margin (`get_margin/`)

`trader.get_margin({"requestType": "NEW", "orders": [...]})` takes the same order dicts as `create_order` and returns `totalFundsRequired` and `marginInfo.totalMargin` (paise). Read-only.

| File | What it checks |
| --- | --- |
| [basic_usage.py](../../examples/trading/get_margin/basic_usage.py) | 1-share ICICIBANK limit order. |
| [example_margin_patterns.py](../../examples/trading/get_margin/example_margin_patterns.py) | 1-share ICICIBANK market order. |
| [example_margin_patterns_02.py](../../examples/trading/get_margin/example_margin_patterns_02.py) | One lot of nearest-expiry HDFCBANK futures (found via `get_instruments_dataframe`). |
| [example_margin_patterns_03.py](../../examples/trading/get_margin/example_margin_patterns_03.py) | One NIFTY long-straddle strategy order. |

```python
print(f"Funds required: Rs {(funds.totalFundsRequired or 0) / 100:,.2f}")
print(f"Total margin:   Rs {(funds.marginInfo.totalMargin or 0) / 100:,.2f}")
```

Real output (limit order, then straddle):

```
LTP: Rs 1316.30
Funds required: Rs 329.62
Total margin:   Rs 329.07

Funds required: Rs 13,337.77
Total margin:   Rs 13,276.25
```

### Modify (`modify_order/`, `modify_flexi_order/`)

Send `orderId` plus the fields you are changing, with `executionMode`. A list modifies several orders in one request. Each script places a resting order, waits 2 seconds, modifies, prints the order, waits 5 seconds, then cancels.

| File | What it modifies |
| --- | --- |
| [modify_order/basic_usage.py](../../examples/trading/modify_order/basic_usage.py) | Price and quantity. |
| [modify_order/example_modify_patterns.py](../../examples/trading/modify_order/example_modify_patterns.py) | Attached stop-loss and target (`exitConfig`). |
| [modify_order/example_modify_patterns_02.py](../../examples/trading/modify_order/example_modify_patterns_02.py) | Entry trigger price and entry price. |
| [modify_order/example_modify_patterns_03.py](../../examples/trading/modify_order/example_modify_patterns_03.py) | Two orders (ICICIBANK, RELIANCE) in one request. |
| [modify_flexi_order/basic_usage.py](../../examples/trading/modify_flexi_order/basic_usage.py) | A strategy order's quantity and net price. Do not resend `legs`, `isMultiLeg`, `refId` or `side`. |

```python
result = trader.modify_orders_sentinel({
    "orderId": order_id,
    "qty": 2,
    "entryPrice": to_tick(ltp * 0.97),
    "deliveryType": "IDAY",
    "priceType": "LIMIT",
    "validityType": "DAY",
    "executionMode": "ENTRY",
})
...
time.sleep(5)  # let the modify settle; an order cannot be cancelled while the exchange is processing a modify
```

Real output:

```
LTP: Rs 1317.90
{'message': 'order modify request pushed successfully'}
Order 19151: OPEN, qty=1, price=Rs 0.00
{'message': 'order cancellation request pushed successfully'}
```

The acknowledgement is not the new state. The order read straight after the modify can still show the old values (here `qty=1`), and the price prints as `Rs 0.00` because the UAT response carries no `entryPrice`.

### Cancel (`cancel_order/`, `cancel_flexi_order/`)

| File | What it does |
| --- | --- |
| [cancel_order/basic_usage.py](../../examples/trading/cancel_order/basic_usage.py) | Cancels a resting order in full (omit `exitTriggerKind`). |
| [cancel_order/example_cancel_patterns.py](../../examples/trading/cancel_order/example_cancel_patterns.py) | Cancels only the stop-loss trigger; the order stays active. Then cancels the order. |
| [cancel_order/example_cancel_patterns_02.py](../../examples/trading/cancel_order/example_cancel_patterns_02.py) | Cancels two orders in one request. |
| [cancel_flexi_order/basic_usage.py](../../examples/trading/cancel_flexi_order/basic_usage.py) | Cancels a strategy order by its strategy-level id. |
| [cancel_order/cancel_all_open_orders.py](../../examples/trading/cancel_order/cancel_all_open_orders.py) | Workflow: cancel everything still working (see Workflows). |

```python
# Cancel only the stop-loss trigger; the order itself stays active.
# exitTriggerKind is one of STOPLOSS, TARGET_PROFIT, TRAILING_STOP.
print(trader.cancel_orders_sentinel([{"orderId": order_id, "exitTriggerKind": "STOPLOSS"}]))
```

Real output (`cancel_order/basic_usage.py`):

```
LTP: Rs 1316.80
{'message': 'order cancellation request pushed successfully'}
Order 19144: OPEN, qty=1, price=Rs 0.00
```

The order is read immediately after the cancel acknowledgement, so it still reads `OPEN`. Poll again to see `CANCELLED`.

### Reading orders (`get_order/`, `get_flexi_order/`)

| File | Type | What it does |
| --- | --- | --- |
| [get_order/get_all_orders_for_the_day.py](../../examples/trading/get_order/get_all_orders_for_the_day.py) | read-only | `trader.orders()` grouped by bucket, plus filters `status=`, `exchange=`, `delivery_type=`, `strat_tags=`. |
| [get_order/get_order_by_id.py](../../examples/trading/get_order/get_order_by_id.py) | places and cancels an order | `trader.get_order(id_or_list)` returns a list. |
| [get_flexi_order/basic_usage.py](../../examples/trading/get_flexi_order/basic_usage.py) | read-only | Strategy orders by tag, with their legs (`isMulti`, `legs[].unitQty`, `filledQty`). |

```python
all_orders = trader.orders()
open_orders = trader.orders(status="OPEN")  # OPEN, EXECUTED, REJECTED, GTE, CANCELLED, EXPIRED
tagged_orders = trader.orders(strat_tags="python-sdk-v3-basic-usage")  # one tag or a list of tags
for group_name, order_list in all_orders.orders.items():
    print(group_name, len(order_list))
```

Orders come grouped by bucket: open, executed, cancelled, rejected, expired and gtt.

Real output (`get_all_orders_for_the_day.py`, first lines):

```
cancelled 70
18970 CANCELLED 0/65 market
18971 CANCELLED 0/1 market
18972 CANCELLED 0/1 market
```

Real output (`get_flexi_order/basic_usage.py`, one executed strategy):

```
executed 18986 EXECUTED net Rs 0.00 ['python-sdk-v3-nifty-buy-straddle']
  leg 1722274 1 65 65
  leg 1722275 1 65 65
```

Each leg line is `refId unitQty orderQty filledQty`.

### Workflows

Scripts to copy into your own code. Each combines two or three calls into one safe routine.

| File | What it does | Type |
| --- | --- | --- |
| [place_order/margin_check_then_place.py](../../examples/trading/place_order/margin_check_then_place.py) | `get_margin`, compare to `netMarginAvailable`, place only if funds cover it. | mutating |
| [place_order/place_and_track_status.py](../../examples/trading/place_order/place_and_track_status.py) | Place, poll `get_order` every second, print each status change. | mutating |
| [place_order/bracket_entry_stoploss_target.py](../../examples/trading/place_order/bracket_entry_stoploss_target.py) | Limit entry with stop-loss and target, sanity check and risk/reward printout. | mutating |
| [place_order/square_off_all_positions.py](../../examples/trading/place_order/square_off_all_positions.py) | `exit_all_positions(at_market_price=True)`; closes every open position. | mutating, closes ALL |
| [place_flexi_order/strategy_margin_precheck.py](../../examples/trading/place_flexi_order/strategy_margin_precheck.py) | Same margin guard for a NIFTY straddle. | mutating |
| [cancel_order/cancel_all_open_orders.py](../../examples/trading/cancel_order/cancel_all_open_orders.py) | Cancel all working orders in batches of 20; optional `TAG` filter. | mutating, cancels ALL |
| [get_order/todays_orders_table.py](../../examples/trading/get_order/todays_orders_table.py) | Today's orders as a table, newest first, with a status count. | read-only |
| [get_order/order_status_monitor.py](../../examples/trading/get_order/order_status_monitor.py) | Poll every 3s for 30s, print NEW / CHANGED lines (no websocket). | read-only |

**Margin guard.** Use one dict for both the check and the placement.

```python
funds = trader.get_margin({"requestType": "NEW", "orders": [order]})
required = funds.totalFundsRequired or 0  # paise
available = portfolio.funds().portFundsAndMargin.netMarginAvailable or 0  # paise
if required > available:
    print(f"Not placing: short by Rs {(required - available) / 100:,.2f}")
    raise SystemExit(0)
result = trader.create_order(order)
```

Real output:

```
LTP: Rs 1317.50
Funds required: Rs 329.96 | available: Rs -29,069.13
Not placing: short by Rs 29,399.09
```

The UAT account has no usable funds, so the guard stops the script. That is the expected outcome here, not an error. UAT itself does not enforce funds on placement, so the same order sent directly would go through. `strategy_margin_precheck.py` behaves the same way:

```
Straddle net premium: Rs 202.75 per unit, lot size 65
Funds required: Rs 13,354.28 | available: Rs -29,069.13
Not placing: short by Rs 42,423.41
```

**Status tracker.** The polling loop prints only on a change:

```python
orders = trader.get_order(order_id) or []  # a new order may take ~1-2s to appear
if orders and (not seen or orders[0].status != seen[-1]):
    seen.append(orders[0].status)
```

Real output:

```
LTP: Rs 1317.50
Placed order 19241 at Rs 1291.20
[12:53:10] order 19241: OPEN, filled 0/1
Cancel: {'message': 'order cancellation request pushed successfully'}
[12:53:19] order 19241: CANCELLED, filled 0/1
Status path: OPEN -> CANCELLED
```

**Bracket order.** Entry below market, stop-loss and target around it. The script checks ordering before sending: `sl_limit <= sl_trigger < entry < tp_trigger`.

```python
entry = to_tick(ltp * 0.98)  # resting buy below market so it does not fill
sl_trigger, sl_limit = to_tick(entry * 0.99), to_tick(entry * 0.989)  # stop-loss limit <= trigger
tp_trigger, tp_limit = to_tick(entry * 1.02), to_tick(entry * 1.019)
```

Real output:

```
LTP: Rs 1319.40
Entry Rs 1293.00 | stop-loss Rs 1280.10 | target Rs 1318.90
Risk Rs 12.90 vs reward Rs 25.90 per share (1:2.0)
Placed order 19176: OPEN
Cancel: {'message': 'order cancellation request pushed successfully'}
```

**Square-off.** The SDK sends one opposite-side order per open position (SELL for long, BUY for short). `at_market_price=True` uses MARKET/IOC; the default exits at LTP with limit orders.

```python
result = trader.exit_all_positions(at_market_price=True)
```

Real output (positions table trimmed; the run sent 14 exit orders):

```
symbol                    net qty   avg (Rs)   ltp (Rs)     P&L (Rs)
RELIANCE                       -4   1,178.75   1,179.30        -1.90
ICICIBANK                      24   1,317.81   1,318.00         0.30
NIFTY26O0622450PE             130      92.80      86.70    -1,088.75
...
Exit order 19242: OPEN
Exit order 19243: OPEN
3 position(s) still open.
```

The re-check three seconds later still showed 3 positions open on that run. Exit orders can lag, so run it again to confirm.

**Cancel all.** Finds every order not in a terminal status (including pending `GTE`), cancels in batches of 20, then re-reads. Real output summary:

```
Cancel: {'message': 'order cancellation request pushed successfully'}
Cancel: {'message': 'order cancellation request pushed successfully'}
Cancelled 23 of 23; 0 still open.
```

**Orders table and monitor.** Real output (`todays_orders_table.py`, first rows):

```
    order id  symbol                 side    qty   price (Rs)  status
       19149  ICICIBANK              BUY       1       market  CANCELLED
       19148  RELIANCE               BUY       1       market  CANCELLED
       19143  strategy (2 legs)      BUY      65       market  CANCELLED
       19134  ICICIBANK              SELL      1       market  EXECUTED
```

`order_status_monitor.py` printed `Watching 116 existing order(s) for 30s...` then `Done.`. Nothing changed during that run, so no `NEW` or `CHANGED` lines appeared. Place or cancel an order from another terminal while it runs to see them.

## Go further

1. Run `margin_check_then_place.py` after changing the quantity to 1000 and compare the funds-required figure. Predict whether the guard stops it, then check.
2. Build a short-side bracket: copy `bracket_entry_stoploss_target.py`, flip `side` to `SELL`, and reverse the ordering check so the stop-loss trigger is above the entry and the target below it.
3. Reuse the `track` function from `place_and_track_status.py` to place a resting order, modify its price, and print the status path. Add a 5-second wait before the cancel.
4. Build a bear put spread from the NIFTY chain using `net_price` and `leg_payload` (long the higher put, short the lower put). Check it with `get_margin` before placing it.

## Common errors

| What you see | Why | Fix |
| --- | --- | --- |
| `Can't cancel this order right now` / `Cancellation is temporarily unavailable while the exchange request is being processed` | Cancel sent while a modify is still being processed by the exchange. | Wait about 5 seconds after a modify. The examples retry the cancel up to 3 times, 3 seconds apart. |
| `ERR011` `You cannot place an order beyond the asset expiry` | `goodTillDate` is after the option's expiry. | Clamp it: `min(now + days, expiry_day)`, as in `place_flexi_order/example_order_patterns_05.py`. |
| `Not placing: short by Rs ...` | Your margin guard found required funds above `netMarginAvailable`. | Add funds or reduce size. The UAT account has about zero funds, so this is expected there. UAT does not enforce funds on placement, so the guard is the only check. |
| Strategy order with `side: "SELL"` is rejected | Strategy orders are always `BUY`. | Use `BUY`, and put the direction in the signed `unitQty` and a signed `entryPrice` (negative for a credit). |
| Price rejected | Prices must be an integer number of paise and a multiple of `tick_size`. | Pass every price through `to_tick`. Never send rupee floats. |
| `get_instrument_by_symbol` returns a dict with `msg` | Symbol not found. | Check `isinstance(instrument, dict)` and exit with `instrument["msg"]`, as every example does. |
| `get_order` returns nothing right after create | The order takes about 1-2 seconds to reach the book. | Sleep 2 seconds, or poll as `place_and_track_status.py` does. |

## Summary

An order is a dict of paise prices snapped to `tick_size`, with one hyphenated tag. Strategies are `BUY` with signed `unitQty` and `entryPrice`. Check margin first, wait about 5 seconds between a modify and a cancel, and confirm state by reading the order rather than trusting the acknowledgement. Develop on UAT.

[Home](README.md) | [← Previous: Realtime Data](04-realtime.md) | [Next: Portfolio →](06-portfolio.md)
