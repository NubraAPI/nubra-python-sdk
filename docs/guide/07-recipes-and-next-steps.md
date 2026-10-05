# 7. Recipes and Next Steps

A task-to-example lookup, three worked workflows, and what to check before going live.

[Home](README.md) | [← Previous: Portfolio](06-portfolio.md)

## In this guide

- Cheat sheet: task to example file
- Worked workflows: options dashboard, safe order ticket, live straddle watch
- Going live checklist
- Keeping up with SDK versions
- Where to get help

All commands run from the repo root with `py -3.12 <path>`.

## Cheat sheet

| Task | Example |
| --- | --- |
| Log in with phone, MPIN and OTP | [otp_login.py](../../examples/authentication/otp_login.py) |
| Log in from `.env` | [using_env_variables_02.py](../../examples/authentication/using_env_variables_02.py) |
| Log in with TOTP | [step_3_login_using_totp.py](../../examples/authentication/step_3_login_using_totp.py) |
| Log out and log in again | [logout_and_relogin.py](../../examples/authentication/logout_and_relogin.py) |
| Switch between UAT and live | [switching_between_uat_and_live.py](../../examples/uat_environment/switching_between_uat_and_live.py) |
| Quick first call | [quick_start.py](../../examples/introduction/quick_start.py) |
| Find an instrument by name | [find_instrument_by_name.py](../../examples/get_instruments/find_instrument_by_name.py) |
| Filtered instrument lookup | [filtered_lookup_example.py](../../examples/get_instruments/filtered_lookup_example.py) |
| Upcoming expiries | [upcoming_expiries.py](../../examples/get_instruments/upcoming_expiries.py) |
| Nearest future | [nearest_future.py](../../examples/get_instruments/nearest_future.py) |
| Index master list | [index_master.py](../../examples/get_instruments/index_master.py) |
| Current price | [basic_usage.py](../../examples/market_data/current_price/basic_usage.py) |
| Watchlist price table | [watchlist_table.py](../../examples/market_data/current_price/watchlist_table.py) |
| Market quote with depth | [basic_usage.py](../../examples/market_data/market_quotes/basic_usage.py) |
| Depth imbalance (REST) | [depth_imbalance.py](../../examples/market_data/market_quotes/depth_imbalance.py) |
| Historical stock candles | [stocks_data.py](../../examples/market_data/historical_market_data/stocks_data.py) |
| Historical index candles | [indices_data.py](../../examples/market_data/historical_market_data/indices_data.py) |
| Expired options data | [expired_options_data.py](../../examples/market_data/historical_market_data/expired_options_data.py) |
| Save OHLC to CSV | [ohlc_to_csv.py](../../examples/market_data/historical_market_data/ohlc_to_csv.py) |
| Option chain | [basic_usage.py](../../examples/market_data/option_chain/basic_usage.py) |
| Option chain as a DataFrame | [option_chain_dataframe.py](../../examples/market_data/option_chain/option_chain_dataframe.py) |
| Compare expiries | [compare_expiries.py](../../examples/market_data/option_chain/compare_expiries.py) |
| Nearest expiry chain | [nearest_expiry.py](../../examples/market_data/option_chain/nearest_expiry.py) |
| Company fundamentals | [basic_usage.py](../../examples/market_data/company_fundamentals/basic_usage.py) |
| Live price stream | [basic_usage.py](../../examples/realtime_data/realtime_data/basic_usage.py) |
| Live index ticker | [multi_index_ticker.py](../../examples/realtime_data/index_data/multi_index_ticker.py) |
| Live OHLCV candles | [basic_usage.py](../../examples/realtime_data/ohlcv_data/basic_usage.py) |
| Stream OHLCV to CSV | [ohlcv_to_csv.py](../../examples/realtime_data/ohlcv_data/ohlcv_to_csv.py) |
| Live option chain | [basic_usage.py](../../examples/realtime_data/option_chain_data/basic_usage.py) |
| Live ATM straddle | [atm_straddle_monitor.py](../../examples/realtime_data/option_chain_data/atm_straddle_monitor.py) |
| Live Greeks | [basic_usage.py](../../examples/realtime_data/greeks_data/basic_usage.py) |
| Greeks alerts | [greeks_alert_watch.py](../../examples/realtime_data/greeks_data/greeks_alert_watch.py) |
| Live order book depth | [depth_imbalance.py](../../examples/realtime_data/order_book_data/depth_imbalance.py) |
| Check margin | [basic_usage.py](../../examples/trading/get_margin/basic_usage.py) |
| Check margin, then place | [margin_check_then_place.py](../../examples/trading/place_order/margin_check_then_place.py) |
| Place an order | [basic_usage.py](../../examples/trading/place_order/basic_usage.py) |
| Place and track status | [place_and_track_status.py](../../examples/trading/place_order/place_and_track_status.py) |
| Entry with stop-loss and target | [bracket_entry_stoploss_target.py](../../examples/trading/place_order/bracket_entry_stoploss_target.py) |
| Place a multi-leg order | [basic_usage.py](../../examples/trading/place_multi_order/basic_usage.py) |
| Flexi order | [basic_usage.py](../../examples/trading/place_flexi_order/basic_usage.py) |
| Modify an order | [basic_usage.py](../../examples/trading/modify_order/basic_usage.py) |
| Cancel an order | [basic_usage.py](../../examples/trading/cancel_order/basic_usage.py) |
| Cancel all open orders | [cancel_all_open_orders.py](../../examples/trading/cancel_order/cancel_all_open_orders.py) |
| Today's orders | [todays_orders_table.py](../../examples/trading/get_order/todays_orders_table.py) |
| Monitor order status | [order_status_monitor.py](../../examples/trading/get_order/order_status_monitor.py) |
| Live order updates | [basic_usage.py](../../examples/trading/realtime_order_updates/basic_usage.py) |
| Square off all positions | [square_off_all_positions.py](../../examples/trading/place_order/square_off_all_positions.py) |
| Funds and margin | [basic_usage.py](../../examples/portfolio/funds/basic_usage.py) |
| Holdings | [basic_usage.py](../../examples/portfolio/holdings/basic_usage.py) |
| Positions | [basic_usage.py](../../examples/portfolio/positions/basic_usage.py) |
| One-screen portfolio summary | [portfolio_summary.py](../../examples/portfolio/portfolio_summary.py) |
| Open positions P&L, worst first | [open_positions_pnl.py](../../examples/portfolio/open_positions_pnl.py) |

## Worked workflows

### 1. Morning options dashboard

Goal: before the open, see the option chain, how expiries compare, and your own exposure. All read-only.

| Step | Read and run | Change |
| --- | --- | --- |
| 1 | [option_chain_dataframe.py](../../examples/market_data/option_chain/option_chain_dataframe.py) | Set your underlying and expiry; keep only the columns you use. |
| 2 | [compare_expiries.py](../../examples/market_data/option_chain/compare_expiries.py) | Pick the two expiries you trade. |
| 3 | [portfolio_summary.py](../../examples/portfolio/portfolio_summary.py) | Keep as is; it supplies margin used, open exposure and P&L. |

Combine: put the three print blocks into one file, create `nubra` and `NubraPortfolio` once, and print the portfolio block first. Call each endpoint once per run.

### 2. Safe order ticket

Goal: no order without a margin check, and always know what happened to it. UAT only until you trust it.

| Step | Read and run | Change |
| --- | --- | --- |
| 1 | [margin_check_then_place.py](../../examples/trading/place_order/margin_check_then_place.py) | Set instrument, quantity, side and price; keep the rule that a failed margin check stops the script. |
| 2 | [place_and_track_status.py](../../examples/trading/place_order/place_and_track_status.py) | Keep the status tracking after placement. |
| 3 | [modify_order/basic_usage.py](../../examples/trading/modify_order/basic_usage.py) | This example places its own test order first. Remove that part and pass in the order id from step 2. |
| 4 | [cancel_order/basic_usage.py](../../examples/trading/cancel_order/basic_usage.py) | Also places its own test order. Remove that part and cancel the order id from step 2. |

Combine: pass the order id from step 2 into steps 3 and 4. Use one tag per order, hyphens only (the examples use `python-sdk-v3-basic-usage`).

### 3. Live straddle watch

Goal: stream the ATM straddle and get alerted when Greeks cross your thresholds.

| Step | Read and run | Change |
| --- | --- | --- |
| 1 | [atm_straddle_monitor.py](../../examples/realtime_data/option_chain_data/atm_straddle_monitor.py) | The underlying is set in the script (`NIFTY`) and the expiry is the nearest one from the option chain. Change both there. |
| 2 | [greeks_alert_watch.py](../../examples/realtime_data/greeks_data/greeks_alert_watch.py) | Set the Greek and threshold for your alerts. |

Combine: use one WebSocket session for both. Streams are limited by session weight, so unsubscribe what you stop using and do not fall back to REST polling.

## Going live checklist

| Check | What to do |
| --- | --- |
| Environment | Change `NubraEnv.UAT` to `NubraEnv.PROD` in `InitNubraSdk(...)`. Every example has a comment at that line. |
| Credentials | `PHONE_NO` and `MPIN` in `.env`, with `.env` kept out of git. Confirm you are logged in to the live account. |
| Quantities | Re-check lot size and quantity on every order. Start with the smallest tradable size. |
| Tags | One tag per order, hyphens only, so orders can be traced. |
| Margin | Run [get_margin](../../examples/trading/get_margin/basic_usage.py) before each order. |
| Rate limits | See the table below. Centralise throttling in one helper and back off on retries. |
| Start small | One instrument, one lot, one strategy. Watch fills with [order_status_monitor.py](../../examples/trading/get_order/order_status_monitor.py). |
| Regression | Keep running the same scripts in UAT after each SDK upgrade or code change. |

Published limits (spec rate-limits page and `schemas/api_rate_limits`):

| API category | Limit |
| --- | --- |
| Trading APIs in PROD | 10 operations per second, per IP (unregistered algo guidance) |
| Trading APIs in UAT | 100 operations per second |
| Historical data | 60 requests per minute |
| Live WebSocket streams | Weight-based, per session |

UAT throughput is not a safe production baseline. Higher PROD throughput needs algo registration through support@nubra.io. Cache historical data and prefer WebSocket subscriptions over REST polling.

## Keeping up with SDK versions

- Release notes: [CHANGELOG.md](../../CHANGELOG.md)
- Version notes for this repo: [VERSIONS.md](../../VERSIONS.md)

| Task | Command |
| --- | --- |
| Check installed version | `python -m pip show nubra-sdk` |
| Upgrade | `python -m pip install --upgrade nubra-sdk` |

After an upgrade, re-run your UAT scripts before using the new version in PROD.

## Where to get help

| Need | Where |
| --- | --- |
| Product and SDK support, algo registration | support@nubra.io |
| Bugs and feature requests | GitHub Issues on the repository |
| Reporting a security problem | [SECURITY.md](../../SECURITY.md) |
| Contributing fixes or examples | [CONTRIBUTING.md](../../CONTRIBUTING.md) |

## Summary

Use the cheat sheet to find the example for a task, then combine examples as in the three workflows. Rehearse in UAT, go live with the checklist, and read the changelog on each upgrade.

[Home](README.md) | [← Previous: Portfolio](06-portfolio.md)
