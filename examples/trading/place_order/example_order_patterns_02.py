from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.trading.trading_data import NubraTrader
from nubra_python_sdk.refdata.instruments import InstrumentData

nubra = InitNubraSdk(NubraEnv.UAT)
instruments = InstrumentData(nubra)
md = MarketData(nubra)
trade = NubraTrader(nubra, version="V2")

ref_id = instruments.get_instrument_by_symbol("RELIANCE", exchange="NSE").ref_id
quote = md.quote(ref_id=ref_id, levels=5)
ltp = quote.orderBook.last_traded_price

result = trade.create_order({
    "ref_id": ref_id,
    "order_type": "ORDER_TYPE_STOPLOSS",
    "order_qty": 1,
    "order_side": "ORDER_SIDE_BUY",
    "order_delivery_type": "ORDER_DELIVERY_TYPE_IDAY",
    "validity_type": "DAY",
    "price_type": "LIMIT",
    "order_price": ltp + 50,
    "exchange": "NSE",
    "tag": "Stoploss_example",
    "algo_params": {
        "trigger_price": ltp + 30
    }
})
