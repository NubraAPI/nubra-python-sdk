# Snippet: Accessing Response Fields

Original source path: `market_data/option_chain/accessing_response_fields.py`

```python
chain = result.chain

print(f"Current Price: {chain.current_price}")
print(f"ATM Strike: {chain.at_the_money_strike}")
print(f"Available Expiries: {chain.all_expiries}")

atm_ce = next((opt for opt in chain.ce if opt.strike_price == chain.at_the_money_strike), None)
atm_pe = next((opt for opt in chain.pe if opt.strike_price == chain.at_the_money_strike), None)

if atm_ce:
    print(atm_ce.ref_id, atm_ce.last_traded_price, atm_ce.open_interest, atm_ce.iv)

if atm_pe:
    print(atm_pe.ref_id, atm_pe.last_traded_price, atm_pe.open_interest, atm_pe.iv)
```
