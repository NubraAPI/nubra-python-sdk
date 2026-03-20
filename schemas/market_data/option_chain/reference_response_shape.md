# Schema Reference: Reference Response Shape

Original source path: `market_data/option_chain/reference_response_shape.py`

```python
class OptionChainWrapper:
    chain: OptionChain
    message: str
    exchange: str | None

class OptionChain:
    asset: str
    expiry: str | None
    ce: list[OptionData]
    pe: list[OptionData]
    at_the_money_strike: int | None
    current_price: int | None
    all_expiries: list[str]

class OptionData:
    ref_id: int
    timestamp: int
    strike_price: int
    lot_size: int
    last_traded_price: int
    last_traded_price_change: float
    iv: float
    delta: float
    gamma: float
    theta: float
    vega: float
    open_interest: int
    open_interest_change: float
    volume: int
```
