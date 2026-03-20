from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.trading.trading_data import NubraTrader
from nubra_python_sdk.trading.trading_enum import ExchangeEnum

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)
market_data = MarketData(nubra)
trader = NubraTrader(nubra, version="V2")

hdfc_ref_id = instruments.get_instrument_by_symbol("HDFCBANK", exchange=ExchangeEnum.NSE).ref_id
reliance_ref_id = instruments.get_instrument_by_symbol("RELIANCE", exchange=ExchangeEnum.NSE).ref_id

hdfc_ltp = market_data.quote(ref_id=hdfc_ref_id, levels=1).orderBook.last_traded_price
reliance_ltp = market_data.quote(ref_id=reliance_ref_id, levels=1).orderBook.last_traded_price

result = trader.multi_order([
    {
        "ref_id": hdfc_ref_id,
        "order_type": "ORDER_TYPE_REGULAR",
        "order_qty": 1,
        "order_side": "ORDER_SIDE_BUY",
        "order_delivery_type": "ORDER_DELIVERY_TYPE_CNC",
        "validity_type": "DAY",
        "price_type": "LIMIT",
        "order_price": hdfc_ltp + 10,
        "exchange": "NSE",
        "tag": "multi_limit_leg"
    },
    {
        "ref_id": reliance_ref_id,
        "order_type": "ORDER_TYPE_STOPLOSS",
        "order_qty": 1,
        "order_side": "ORDER_SIDE_BUY",
        "order_delivery_type": "ORDER_DELIVERY_TYPE_IDAY",
        "validity_type": "DAY",
        "price_type": "LIMIT",
        "order_price": reliance_ltp + 50,
        "exchange": "NSE",
        "tag": "multi_stoploss_leg",
        "algo_params": {
            "trigger_price": reliance_ltp + 30
        }
    }
])

print(result.orders)
