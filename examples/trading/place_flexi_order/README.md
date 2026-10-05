All of these call `trader.create_order()`: a list of dicts for multi, one dict with `isMultiLeg: True` for a strategy. `side` is always `BUY`, even for a net credit.

# Strategy orders (`place_flexi_order/`)

Each pattern builds legs from the NIFTY option chain around the ATM strike and sends one `isMultiLeg: True` order. Direction per leg comes from the sign of `legs[].unitQty`; `entryPrice` is the signed net premium in paise (negative for a net credit).

| File | What it does |
| --- | --- |
| `basic_usage.py` | Long straddle with trigger entry, stop-loss and target. |
| `example_order_patterns.py` | Long straddle. |
| `example_order_patterns_02.py` | Long strangle. |
| `example_order_patterns_03.py` | Iron condor. |
| `example_order_patterns_04.py` | Iron butterfly. |
| `example_order_patterns_05.py` | Bull call spread with `GTE`, trigger entry, trailing stop-loss and target. |
| `example_order_patterns_06.py` | Bear call spread (net credit, negative `entryPrice`). |
| `strategy_margin_precheck.py` | Margin pre-check for a NIFTY straddle, then place only if funds cover it. |

Type: mutating (UAT). Test orders are cancelled at the end where they can still be cancelled. See [../README.md](../README.md) for conventions.
