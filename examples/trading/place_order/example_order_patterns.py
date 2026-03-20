from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.trading.trading_data import NubraTrader
from nubra_python_sdk.refdata.instruments import InstrumentData

nubra = InitNubraSdk(NubraEnv.UAT)
instruments = InstrumentData(nubra)
md = MarketData(nubra)
trade = NubraTrader(nubra, version="V2")

ref_id = instruments.get_instrument_by_symbol("HDFCBANK", exchange="NSE").ref_id
quote = md.quote(ref_id=ref_id, levels=5)
ltp = quote.orderBook.last_traded_price

result = trade.create_order({
    "ref_id": ref_id,
    "order_type": "ORDER_TYPE_REGULAR",
    "order_qty": 1,
    "order_side": "ORDER_SIDE_BUY",
    "order_delivery_type": "ORDER_DELIVERY_TYPE_CNC",
    "validity_type": "DAY",
    "price_type": "LIMIT",
    "order_price": ltp + 90,
    "exchange": "NSE",
    "tag": "Limit_example"
})
