# Schema Reference: Reference Response Shape

Original source path: `market_data/option_chain/reference_response_shape.py`

```python
class OptionChainWrapper:
    chain: OptionChain
    message: str
    exchange: str | None

class OptionChain:
    asset: str
    expiry: str
    ce: list[OptionData]
    pe: list[OptionData]
    at_the_money_strike: int | None
    current_price: int | None
    all_expiries: list[str]
    underlying_instrument: UnderlyingInstrument | None  # in installed SDK, not in docs

class OptionData:
    ref_id: int
    timestamp: int | None
    strike_price: int
    lot_size: int | None
    last_traded_price: int | None
    last_traded_price_change: float | None
    iv: float | None
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None
    open_interest: int | None
    previous_open_interest: int | None  # docs say open_interest_change (float); installed SDK differs
    volume: int | None
```
