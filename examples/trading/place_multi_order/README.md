All of these call `trader.create_order()`: a list of dicts for multi, one dict with `isMultiLeg: True` for a strategy. `side` is always `BUY`, even for a net credit.

# Multi orders (`place_multi_order/`)

Pass a list of dicts to `create_order` to send several independent orders in one request. Each item has its own `refId`, tick size and `stratTags` (a list with exactly one hyphenated tag). These are not linked legs.

| File | What it does |
| --- | --- |
| `basic_usage.py` | BUY ICICIBANK and SELL RELIANCE, both limit. |
| `example_order_patterns.py` | Same two-limit-order request. |
| `example_order_patterns_02.py` | A plain limit order plus a limit order with a stop-loss exit. |
| `example_order_patterns_03.py` | A limit order plus a market order (the market leg fills and opens a position). |

Type: mutating (UAT). Test orders are cancelled at the end where they can still be cancelled. See [../README.md](../README.md) for conventions.
