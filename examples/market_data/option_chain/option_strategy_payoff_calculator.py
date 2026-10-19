"""Payoff, max profit, max loss and breakevens for a multi-leg option strategy, priced from the live chain.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: the bull call spread legs (ATM call bought, a call 5 strikes higher sold) priced from the live NIFTY
        chain, then max profit, max loss and breakeven in rupees. Nothing is ordered.
Tested with: nubra-sdk 0.5.4 (UAT)

`strategy_payoff()` is plain Python and works for any number of legs; only the leg prices come from the SDK.
Max profit and max loss are taken over the underlying range you pass in, so for strategies with unlimited
risk or reward they describe that range, not the whole payoff curve. This is a calculator, not a recommendation.
"""
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv


def strategy_payoff(legs, underlying_range):
    """Payoff at expiry for each underlying price, plus max profit, max loss and breakevens.

    Each leg is a dict with: type ('call'/'put'), action ('buy'/'sell'), strike, premium (per unit),
    lots, lot_size. Returns {'payoffs': [(price, pnl), ...], 'max_profit', 'max_loss', 'breakevens'}.
    """
    payoffs = []
    for price in underlying_range:
        total = 0.0
        for leg in legs:
            qty = leg["lots"] * leg["lot_size"]
            if leg["type"] == "call":
                intrinsic = max(price - leg["strike"], 0)
            else:
                intrinsic = max(leg["strike"] - price, 0)
            if leg["action"] == "buy":
                total += (intrinsic - leg["premium"]) * qty
            else:
                total += (leg["premium"] - intrinsic) * qty
        payoffs.append((price, round(total, 2)))

    pnl_values = [pnl for _, pnl in payoffs]

    # Breakevens: where the payoff crosses (or touches) zero, with linear interpolation between points.
    breakevens = []
    for i, (price, pnl) in enumerate(payoffs):
        if pnl == 0:
            breakevens.append(round(price, 2))
        elif i and payoffs[i - 1][1] * pnl < 0:
            prev_price, prev_pnl = payoffs[i - 1]
            breakevens.append(round(prev_price + (0 - prev_pnl) * (price - prev_price) / (pnl - prev_pnl), 2))

    return {"payoffs": payoffs, "max_profit": max(pnl_values), "max_loss": min(pnl_values), "breakevens": breakevens}


# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
result = MarketData(nubra).option_chain("NIFTY", exchange="NSE")
if result is None:
    raise SystemExit("No option chain returned (check symbol / exchange / expiry)")
chain = result.chain

# Strikes and prices arrive in paise.
calls = {o.strike_price: o for o in chain.ce if o.last_traded_price and o.lot_size}
strikes = sorted(calls)
atm = chain.at_the_money_strike
if atm not in calls or strikes.index(atm) + 5 >= len(strikes):
    raise SystemExit("Not enough priced call strikes around ATM to build the spread")
buy_leg = calls[atm]
sell_leg = calls[strikes[strikes.index(atm) + 5]]

legs = [
    {"type": "call", "action": "buy", "strike": buy_leg.strike_price / 100,
     "premium": buy_leg.last_traded_price / 100, "lots": 1, "lot_size": buy_leg.lot_size},
    {"type": "call", "action": "sell", "strike": sell_leg.strike_price / 100,
     "premium": sell_leg.last_traded_price / 100, "lots": 1, "lot_size": sell_leg.lot_size},
]
for leg in legs:
    print(f"{leg['action'].upper():4} 1 lot {leg['strike']:,.0f} CE @ Rs {leg['premium']:,.2f} (lot size {leg['lot_size']})")

# Evaluate expiry prices from 5% below the lower strike to 5% above the higher one, in 25-point steps.
low, high = legs[0]["strike"] * 0.95, legs[1]["strike"] * 1.05
underlying_range = [low + 25 * i for i in range(int((high - low) // 25) + 1)]
outcome = strategy_payoff(legs, underlying_range)

print(f"Expiry {chain.expiry} | spot Rs {chain.current_price / 100:,.2f}")
print(f"Max profit: Rs {outcome['max_profit']:,.0f}")
print(f"Max loss:   Rs {outcome['max_loss']:,.0f}")
print(f"Breakevens: {outcome['breakevens']}")
print("(Finer underlying steps give more precise breakevens.)")
