# Trading examples (Nubra Python SDK, Trading API V3)

**Run on UAT first.** Every script defaults to `NubraEnv.UAT`. Switch to `NubraEnv.PROD` only after you have read the script and understand what it will do. Mutating scripts place real orders in PROD.

Conventions used throughout:

- Prices and money are integer **paise** in requests and responses. Scripts print rupees (paise / 100) for readability; request payloads stay in paise.
- Orders placed only for demonstration are priced to rest (below market) and cancelled at the end where the order can still be cancelled.
- Strategy (multi-leg) orders always use `side: "BUY"`; leg direction comes from the sign of `legs[].unitQty`, and `entryPrice` is the signed net premium.
- `modify` followed by `cancel` needs about 5 seconds between them, otherwise the exchange rejects the cancel while the modify is processing.
- Each script has a docstring at the top: what it does, `Type`, `Needs`, `Expect`.

Type: **read-only** never places or changes orders. **mutating (UAT)** places, modifies or cancels orders.

## Workflow examples (start here)

| File | What it does | Type |
| --- | --- | --- |
| `place_order/margin_check_then_place.py` | Check margin, place the order only if available funds cover it | mutating (UAT) |
| `place_order/place_and_track_status.py` | Place an order, poll `get_order`, print each status change until it settles | mutating (UAT) |
| `place_order/bracket_entry_stoploss_target.py` | Equity entry with stop-loss and target, with risk/reward printout | mutating (UAT) |
| `place_order/square_off_all_positions.py` | Close every open position with market orders (`exit_all_positions`) | mutating (UAT), closes ALL positions |
| `place_flexi_order/strategy_margin_precheck.py` | Margin pre-check for a NIFTY straddle strategy, then place | mutating (UAT) |
| `cancel_order/cancel_all_open_orders.py` | Cancel all open orders (optionally by tag); UAT cleanup helper | mutating (UAT), cancels ALL open orders |
| `get_order/todays_orders_table.py` | Today's orders as a table (id, symbol, side, qty, Rs price, status) | read-only |
| `get_order/order_status_monitor.py` | Poll orders for 30s and print status changes (no websocket) | read-only |

## Reference examples

| Folder | Files | What they cover | Type |
| --- | --- | --- | --- |
| `overview/` | `basic_usage.py` | Log in and create `NubraTrader` | read-only |
| `place_order/` | `basic_usage.py`, `example_order_patterns*.py` (01-09) | Single orders: limit, trigger + stop-loss, iceberg, market, trailing stop-loss, stop-loss + target, GTE, timed entry/exit | mutating (UAT); the market order (04) fills and is not cancelled |
| `place_multi_order/` | `basic_usage.py`, `example_order_patterns*.py` (01-03) | Several independent orders in one request | mutating (UAT); the market leg in 03 fills |
| `place_flexi_order/` | `basic_usage.py`, `example_order_patterns*.py` (01-06) | NIFTY strategy orders: straddle, strangle, iron condor, iron butterfly, bull call spread (GTE), bear call spread | mutating (UAT) |
| `modify_order/` | `basic_usage.py`, `example_modify_patterns*.py` (01-03) | Modify price/qty, stop-loss/target, trigger, and several orders at once | mutating (UAT) |
| `modify_flexi_order/` | `basic_usage.py` | Modify a strategy order's quantity and net price | mutating (UAT) |
| `cancel_order/` | `basic_usage.py`, `example_cancel_patterns*.py` (01-02) | Cancel an order, only its stop-loss trigger, or several orders | mutating (UAT) |
| `cancel_flexi_order/` | `basic_usage.py` | Cancel a strategy order | mutating (UAT) |
| `get_order/` | `get_all_orders_for_the_day.py`, `get_order_by_id.py` | List/filter orders; fetch one order by id | read-only / mutating (UAT) |
| `get_flexi_order/` | `basic_usage.py` | List strategy orders by tag with their legs | read-only |
| `get_margin/` | `basic_usage.py`, `example_margin_patterns*.py` (01-03) | Margin for limit, market, futures and strategy orders | read-only |

Realtime order updates (websocket) live in `realtime_order_updates/`.
