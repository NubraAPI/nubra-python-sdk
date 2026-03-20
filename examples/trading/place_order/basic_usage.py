from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.trading.trading_data import NubraTrader
from nubra_python_sdk.trading.trading_enum import ExchangeEnum

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)
market_data = MarketData(nubra)
trader = NubraTrader(nubra, version="V2")

ref_id = instruments.get_instrument_by_symbol("HDFCBANK", exchange=ExchangeEnum.NSE).ref_id
ltp = market_data.quote(ref_id=ref_id, levels=1).orderBook.last_traded_price

result = trader.create_order({
    "ref_id": ref_id,
    "order_type": "ORDER_TYPE_REGULAR",
    "order_qty": 1,
    "order_side": "ORDER_SIDE_BUY",
    "order_delivery_type": "ORDER_DELIVERY_TYPE_CNC",
    "validity_type": "DAY",
    "price_type": "LIMIT",
    "order_price": ltp + 10,
    "exchange": "NSE",
    "tag": "example_single_order"
})

print(result.order_id)
