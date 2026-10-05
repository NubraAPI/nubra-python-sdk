# Schemas

Response shapes and SDK surface notes. `reference_response_shape`, `response_shape` and `response_structure` files list the fields and types an SDK call returns; `sdk_surface` files list call signatures and allowed arguments. Short code fragments are in [../snippets](../snippets/README.md).

## Limits

- [api_rate_limits.md](api_rate_limits.md): rate limits for trading APIs (PROD and UAT), historical data and websocket streams.

## Authentication and instruments

- [authentication/sdk_surface.md](authentication/sdk_surface.md): `InitNubraSdk` arguments and session helpers.
- [get_instruments/sdk_surface.md](get_instruments/sdk_surface.md): `InstrumentData` methods and the `exchange` argument.
- [get_instruments/reference_response_shape.md](get_instruments/reference_response_shape.md): the `Instrument` fields, including `tick_size` and `lot_size`.

## Market data

- [market_data/current_price/sdk_surface.md](market_data/current_price/sdk_surface.md): `MarketData.current_price` signature.
- [market_data/current_price/reference_response_shape.md](market_data/current_price/reference_response_shape.md): `CurrentPrice` fields.
- [market_data/current_price/sample_response.md](market_data/current_price/sample_response.md): sample `current_price` output.
- [market_data/market_quotes/sdk_surface.md](market_data/market_quotes/sdk_surface.md): `MarketData.quote` signature.
- [market_data/market_quotes/reference_response_shape.md](market_data/market_quotes/reference_response_shape.md): order book and level fields.
- [market_data/option_chain/sdk_surface.md](market_data/option_chain/sdk_surface.md): `MarketData.option_chain` signature.
- [market_data/option_chain/reference_response_shape.md](market_data/option_chain/reference_response_shape.md): option chain and per-strike fields.
- [market_data/historical_market_data/sdk_surface.md](market_data/historical_market_data/sdk_surface.md): `historical_data` request keys.
- [market_data/historical_market_data/reference_response_shape.md](market_data/historical_market_data/reference_response_shape.md): chart response fields.
- [market_data/company_fundamentals/sdk_surface.md](market_data/company_fundamentals/sdk_surface.md): fundamentals methods and enums.
- [market_data/company_fundamentals/reference_response_shape.md](market_data/company_fundamentals/reference_response_shape.md): key ratios, statements, shareholding and corporate action fields.

## Realtime data

- [realtime_data/index_data/response_shape.md](realtime_data/index_data/response_shape.md): index tick fields.
- [realtime_data/ohlcv_data/response_shape.md](realtime_data/ohlcv_data/response_shape.md): OHLCV candle fields.
- [realtime_data/option_chain_data/response_shape.md](realtime_data/option_chain_data/response_shape.md): streamed option chain fields.
- [realtime_data/order_book_data/response_shape.md](realtime_data/order_book_data/response_shape.md): market depth fields.
- [realtime_data/greeks_data/response_shape.md](realtime_data/greeks_data/response_shape.md): streamed Greeks fields.

## Trading

- [trading/place_order/response_structure.md](trading/place_order/response_structure.md): what `trader.create_order(...)` returns.
- [trading/get_order/response_structure.md](trading/get_order/response_structure.md): what `trader.orders(...)` and `trader.get_order(...)` return.
- [trading/get_margin/response_structure.md](trading/get_margin/response_structure.md): what `trader.get_margin(...)` returns.
