from datetime import datetime
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader
from nubra_python_sdk.trading.trading_enum import (
    DeliveryTypeEnum,
    OrderSideEnum,
    PriceTypeEnumV2,
    ExchangeEnum,
)

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)
market_data = MarketData(nubra)
trader = NubraTrader(nubra, version="V2")

def get_ref_id(asset, strike, expiry, option_type):
    expiry = datetime.strptime(expiry, "%d-%m-%Y").strftime("%Y%m%d")
    result = instruments.get_instruments_by_pattern([{
        "asset": asset,
        "strike_price": str(strike * 100),
        "expiry": expiry,
        "option_type": option_type,
    }])
    return result[0].ref_id if result else None

def get_ltp(asset, strike, expiry, option_type):
    ref_id = get_ref_id(asset, strike, expiry, option_type)
    quote = market_data.quote(ref_id=ref_id, levels=1)
    return ref_id, quote.orderBook.last_traded_price

short_call_ref_id, short_call_ltp = get_ltp("NIFTY", 23600, "17-03-2026", "CE")
short_put_ref_id, short_put_ltp = get_ltp("NIFTY", 23600, "17-03-2026", "PE")
long_call_ref_id, long_call_ltp = get_ltp("NIFTY", 23900, "17-03-2026", "CE")
long_put_ref_id, long_put_ltp = get_ltp("NIFTY", 23200, "17-03-2026", "PE")

result = trader.flexi_order({
    "exchange": ExchangeEnum.NSE,
    "basket_name": "NIFTY_IronButterfly",
    "tag": "iron_butterfly_example",
    "orders": [
        {
            "ref_id": short_call_ref_id,
            "order_qty": 65,
            "order_side": OrderSideEnum.ORDER_SIDE_SELL,
        },
        {
            "ref_id": short_put_ref_id,
            "order_qty": 65,
            "order_side": OrderSideEnum.ORDER_SIDE_SELL,
        },
        {
            "ref_id": long_call_ref_id,
            "order_qty": 65,
            "order_side": OrderSideEnum.ORDER_SIDE_BUY,
        },
        {
            "ref_id": long_put_ref_id,
            "order_qty": 65,
            "order_side": OrderSideEnum.ORDER_SIDE_BUY,
        },
    ],
    "basket_params": {
        "order_side": OrderSideEnum.ORDER_SIDE_BUY,
        "order_delivery_type": DeliveryTypeEnum.ORDER_DELIVERY_TYPE_CNC,
        "price_type": PriceTypeEnumV2.LIMIT,
        "entry_price": -short_call_ltp - short_put_ltp + long_call_ltp + long_put_ltp + 100,
        "multiplier": 1,
    }
})

print(result.basket_id)
