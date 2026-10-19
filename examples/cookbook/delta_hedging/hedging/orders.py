"""Order gate: every order in this example goes through here.

Orders are OFF by default. Without ``--place-orders`` the gate only prints the
payload it would have sent. With ``--place-orders`` it calls the SDK, and on
PROD it additionally requires ``--allow-prod``.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .session import check_order_flags


class OrderGate:
    def __init__(self, nubra, *, place_orders: bool, env_name: str, allow_prod: bool) -> None:
        check_order_flags(env_name, place_orders, allow_prod)
        from nubra_python_sdk.trading.trading_data import NubraTrader

        self.trader = NubraTrader(nubra)
        self.live = place_orders
        self.env_name = env_name

    @property
    def mode(self) -> str:
        return f"LIVE {self.env_name.upper()}" if self.live else "DRY-RUN"

    def send(self, orders: List[Dict[str, Any]], label: str) -> Optional[list]:
        """Place ``orders`` (paise prices) or print them in dry-run mode.

        Returns the SDK order responses when live, ``None`` in dry-run.
        """
        print(f"[{self.mode}] {label}: {json.dumps(orders)}")
        if not self.live:
            return None
        result = self.trader.create_order(orders)
        responses = list(result.orders)
        for o in responses:
            msg = f" rejected: {o.rejectionMsg}" if o.rejectionMsg else ""
            print(f"  order {o.intentOrderId}: {o.status or 'SUBMITTED'}{msg}")
        return responses

    def flatten_all(self, label: str):
        """Square off every open position on the account with market orders."""
        if not self.live:
            print(f"[{self.mode}] {label}: would call exit_all_positions(at_market_price=True)")
            return None
        print(f"[{self.mode}] {label}: exit_all_positions(at_market_price=True)")
        result = self.trader.exit_all_positions(at_market_price=True)
        for o in (result.orders if result else []):
            msg = f" rejected: {o.rejectionMsg}" if o.rejectionMsg else ""
            print(f"  exit order {o.intentOrderId}: {o.status or 'SUBMITTED'}{msg}")
        return result
