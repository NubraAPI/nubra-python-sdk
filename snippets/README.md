# Snippets

Short code or text fragments, each usable on its own. For full runnable scripts see [../examples](../examples); for response shapes and call signatures see [../schemas](../schemas/README.md).

## Authentication
- [authentication/basic_usage_02.md](authentication/basic_usage_02.md): `nubra.logout()`.
- [authentication/using_env_variables.md](authentication/using_env_variables.md): `.env` for OTP login.
- [authentication/institutional_login_env.md](authentication/institutional_login_env.md): `.env` for institutional login.

## Instruments
- [get_instruments/instruments_master.md](get_instruments/instruments_master.md): load the instruments dataframe for NSE, BSE or MCX.

## Introduction and release notes
- [introduction/before_you_install.md](introduction/before_you_install.md): check the Python version (`python --version`).
- [introduction/before_you_install_02.md](introduction/before_you_install_02.md): check the Python version (`python3 --version`).
- [introduction/installation.md](introduction/installation.md): `python -m pip install nubra-sdk`.
- [introduction/installation_02.md](introduction/installation_02.md): `python3 -m pip install nubra-sdk`.
- [introduction/installation_03.md](introduction/installation_03.md): `python -m pip install --upgrade nubra-sdk`.
- [release_notes/how_to_update.md](release_notes/how_to_update.md): `pip install --upgrade nubra-sdk`.

## Market data
- [market_data/current_price/accessing_response_fields.md](market_data/current_price/accessing_response_fields.md): read `current_price` fields.
- [market_data/market_quotes/accessing_response_fields.md](market_data/market_quotes/accessing_response_fields.md): read order book fields from `quote`.
- [market_data/option_chain/accessing_response_fields.md](market_data/option_chain/accessing_response_fields.md): read the chain, ATM strike and ATM call/put.
- [market_data/historical_market_data/accessing_response_fields.md](market_data/historical_market_data/accessing_response_fields.md): loop over historical series.
- [market_data/company_fundamentals/accessing_key_ratios.md](market_data/company_fundamentals/accessing_key_ratios.md): key ratios and shareholding keys.
- [market_data/company_fundamentals/accessing_financial_statements.md](market_data/company_fundamentals/accessing_financial_statements.md): cash flow, balance sheet and profit and loss.
- [market_data/company_fundamentals/accessing_shareholding_pattern.md](market_data/company_fundamentals/accessing_shareholding_pattern.md): shareholding pattern by date.
- [market_data/company_fundamentals/accessing_corporate_actions.md](market_data/company_fundamentals/accessing_corporate_actions.md): corporate actions list.

## Portfolio
- [portfolio/funds/accessing_data.md](portfolio/funds/accessing_data.md): read `portFundsAndMargin` fields.
- [portfolio/holdings/accessing_data.md](portfolio/holdings/accessing_data.md): read holdings and `holdingStats`.
- [portfolio/positions/accessing_data.md](portfolio/positions/accessing_data.md): read positions and `positionStats`.

## Realtime data
- [realtime_data/realtime_data/callback_model.md](realtime_data/realtime_data/callback_model.md): `NubraDataSocket` with all callbacks.
- [realtime_data/realtime_data/common_subscription_pattern.md](realtime_data/realtime_data/common_subscription_pattern.md): subscribe calls for each stream.
- [realtime_data/realtime_data/unsubscribe_and_close.md](realtime_data/realtime_data/unsubscribe_and_close.md): connect, subscribe, unsubscribe, close.
- [realtime_data/ohlcv_data/supported_intervals.md](realtime_data/ohlcv_data/supported_intervals.md): OHLCV intervals.
- [realtime_data/subscription_limits/weight_table.md](realtime_data/subscription_limits/weight_table.md): weight per stream; session limit 50,000.
- [realtime_data/subscription_limits/quick_examples.md](realtime_data/subscription_limits/quick_examples.md): a mix that totals 9,000 of 50,000.
- [realtime_data/subscription_limits/quick_examples_02.md](realtime_data/subscription_limits/quick_examples_02.md): 1,000 option chains = 20,000.
- [realtime_data/subscription_limits/quick_examples_03.md](realtime_data/subscription_limits/quick_examples_03.md): 2,600 option chains = 52,000, over the limit.

## Trading
- [trading/limit_order.py](trading/limit_order.py): Minimal limit order using trader.create_order.
- [trading/get_order/accessing_data.md](trading/get_order/accessing_data.md): read `trader.orders()` by bucket.
- [trading/get_order/accessing_data_02.md](trading/get_order/accessing_data_02.md): read `trader.get_order(...)` fields.
- [trading/get_order/example_order_lifecycle.md](trading/get_order/example_order_lifecycle.md): get, modify and cancel an order by `intentOrderId`.
- [trading/realtime_order_updates/v3_callbacks.md](trading/realtime_order_updates/v3_callbacks.md): order and trade update callbacks.
- [trading/realtime_order_updates/running_in_a_background_thread.md](trading/realtime_order_updates/running_in_a_background_thread.md): run the order-update socket in a thread.
