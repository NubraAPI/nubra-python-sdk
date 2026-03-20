from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.trading.trading_data import NubraTrader
from nubra_python_sdk.refdata.instruments import InstrumentData

nubra = InitNubraSdk(NubraEnv.UAT)
md = MarketData(nubra)
instruments = InstrumentData(nubra)
trade = NubraTrader(nubra, version="V2")

instrument = instruments.get_instrument_by_symbol("RELIANCE", exchange="NSE")
ref_id = instrument.ref_id

quote = md.quote(ref_id=ref_id, levels=5)
ltp = quote.orderBook.last_traded_price

total_qty = 1000
leg_size = 100

result = trade.create_order({
    "ref_id": ref_id,
    "order_type": "ORDER_TYPE_ICEBERG",
    "order_qty": total_qty,
    "order_side": "ORDER_SIDE_BUY",
    "order_delivery_type": "ORDER_DELIVERY_TYPE_CNC",
    "validity_type": "DAY",
    "price_type": "LIMIT",
    "order_price": ltp + 10,
    "exchange": "NSE",
    "tag": "iceberg_example",
    "algo_params": {
        "leg_size": leg_size
    }
})
