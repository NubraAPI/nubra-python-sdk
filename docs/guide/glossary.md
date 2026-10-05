# Glossary

Exact field names, method names and allowed values used in the trading, portfolio and market-data examples. Payload details are in [Trading](05-trading.md).

[Home](README.md)

## Methods that exist

Order methods are on `NubraTrader` (`trader = NubraTrader(nubra)`, where `nubra` is the client returned by `InitNubraSdk(...)`).

| Method | What it does |
|---|---|
| `trader.create_order(...)` | Places a single order (one dict), several orders (a list of dicts) or a strategy (one dict with `isMultiLeg: True`). |
| `trader.modify_orders_sentinel(...)` | Modifies an order. The SDK requires only `orderId`; optional keys are `refId`, `qty`, `entryPrice`, `goodTillDate`, `entryConfig`, `exitConfig`, `deliveryType`, `priceType`, `validityType`, `executionMode`, `icebergInfo`. The UAT-tested examples send `orderId`, the changed fields, plus `deliveryType`, `priceType`, `validityType` and `executionMode`. |
| `trader.cancel_orders_sentinel(...)` | Cancels one or more orders. Wait about 5 seconds after a modify before cancelling; the examples retry. |
| `trader.get_order(...)` | Returns a list of orders for the given `intentOrderId` (or list of ids). |
| `trader.orders(...)` | The day's orders grouped by bucket (open, executed, cancelled, rejected, expired, gtt). Filters: `status`, `symbol`, `delivery_type`, `exchange`, `strat_tags` (a string or a list of strings). |
| `trader.get_margin(...)` | Margin required for an order payload. |
| `portfolio.funds()` | `portfolio = NubraPortfolio(nubra)` with `from nubra_python_sdk.portfolio.portfolio_data import NubraPortfolio`. Read `.portFundsAndMargin.netMarginAvailable`. |
| `portfolio.holdings()` | Read `.portfolio.holdingStats`. |
| `portfolio.positions()` | Read `.portfolio.positions`. |

**Methods that do not exist:** `place_order`, `place_multi_order`, `place_flexi_order`, `get_holdings`, `get_positions`. The first three are folder names under `examples/trading/`; use `create_order`. For holdings and positions use `portfolio.holdings()` and `portfolio.positions()`.

## Order payload fields

| Term | Field or method | Allowed values and meaning |
|---|---|---|
| executionMode | `executionMode` | `ENTRY` (entry only) or `ENTRY_AND_EXIT` (entry plus an `exitConfig` with stop-loss and/or target). |
| validityType | `validityType` | `DAY`, `IOC`, `GTE`, `AMO`. |
| IOC | `validityType` value | Immediate or cancel. A `validityType` only, never a `priceType`. The market-order example uses `MARKET` with `IOC`. |
| GTE | `validityType` value | Good till expiry. The order stays live across sessions until expiry or fill. Needs `goodTillDate` and, in the strategy examples, `deliveryType: "CNC"`. `goodTillDate` must not be after the option expiry. |
| priceType | `priceType` | `LIMIT` or `MARKET`. Iceberg is not a `priceType`. |
| icebergInfo | `icebergInfo` | Splits an order into legs. Set one of `maxQtyPerLeg` or `numberOfLegs`, not both. |
| deliveryType | `deliveryType` | `IDAY` (intraday) or `CNC` (delivery). |
| entryConfig | `entryConfig` | `triggers.ltp.atOrAbove.value` for a trigger entry, or `entryTime` for a timed entry. |
| exitConfig | `exitConfig` | `stoplossParams`, `targetParams` or `exitTime`. |
| stoplossParams | inside `exitConfig` | `stoplossTriggerPrice`, `stoplossLimitPrice`, optional `stoplossTrailJump`. |
| targetParams | inside `exitConfig` | `targetProfitTriggerPrice`, `targetProfitLimitPrice`. |
| triggers | inside `entryConfig` | Entry trigger condition, for example `{"ltp": {"atOrAbove": {"value": trigger_price}}}`. |
| stratTags | `stratTags` | On placement: a list with exactly one tag, hyphens only. The `strat_tags` filter on `trader.orders(...)` takes a string or a list. |
| isMultiLeg | `isMultiLeg` | `False` for a single order, `True` for a strategy. |
| unitQty | `legs[].unitQty` | Signed quantity per strategy leg: `1` long, `-1` short. |
| entryPrice | `entryPrice` | Limit price in paise. For a strategy, the signed net premium in paise; negative means a net credit. Omit for `MARKET`. |
| side | `side` | `BUY` or `SELL` for single orders. Strategy orders are always `BUY`, credit or debit; direction comes from signed `unitQty` and signed `entryPrice`. |

## Instruments and prices

| Term | Meaning |
|---|---|
| paise | Prices in requests and responses are integers in paise (116770 is Rs 1167.70). |
| tick_size | Instrument field, in paise. Round every order price to a multiple of it with the `to_tick()` helper defined in the trading examples. |
| ref_id | Numeric id of a contract, from `get_instrument_by_symbol(...).ref_id`. It can differ between UAT and PROD, so resolve it by symbol in each environment. The order-book and Greeks streams take it as a string. |
| ATM | At-the-money strike, `chain.at_the_money_strike` on an option chain. |
| PCR | Put/call ratio: total put open interest divided by total call open interest (open interest, not volume). A calculation, not a trading signal. |
| IV skew | In `option_chain_dataframe.py`: OTM put IV 3 strikes below ATM minus OTM call IV 3 strikes above ATM. A calculation, not a trading signal. |

[Home](README.md)
