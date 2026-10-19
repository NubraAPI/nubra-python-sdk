"""Book-keeping: option legs, the futures hedge, and net Greeks / P&L.

Units: every rupee field here is in whole rupees, already converted from
Nubra's integer paise at the API boundary (`nubra_client.paise_to_rupees`), so
this module never deals with paise.

Sign convention: `qty_lots` is signed (positive = long, negative = short). A
leg's contribution to net delta/gamma is `greek_per_unit * qty_lots * lot_size`.
Futures have delta 1 and gamma 0 per unit, so a futures position contributes
`qty_lots * lot_size` to net delta and nothing to net gamma.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OptionLeg:
    ref_id: int
    option_type: str  # "CE" or "PE"
    strike: float
    lot_size: int
    qty_lots: int  # signed: negative for a short leg
    entry_price_rupees: float
    current_price_rupees: float = 0.0
    delta: float = 0.0
    gamma: float = 0.0
    greeks_source: str = "unset"  # "api" or "black_scholes"

    def delta_contribution(self) -> float:
        return self.delta * self.qty_lots * self.lot_size

    def gamma_contribution(self) -> float:
        return self.gamma * self.qty_lots * self.lot_size

    def pnl(self) -> float:
        return self.qty_lots * self.lot_size * (self.current_price_rupees - self.entry_price_rupees)


@dataclass
class FuturesPosition:
    ref_id: int
    lot_size: int
    qty_lots: int = 0
    avg_entry_price_rupees: float = 0.0
    current_price_rupees: float = 0.0
    realized_pnl_rupees: float = 0.0

    def delta_contribution(self) -> float:
        return self.qty_lots * self.lot_size

    def unrealized_pnl(self) -> float:
        return self.qty_lots * self.lot_size * (self.current_price_rupees - self.avg_entry_price_rupees)

    def total_pnl(self) -> float:
        return self.realized_pnl_rupees + self.unrealized_pnl()

    def apply_fill(self, signed_qty_lots: int, fill_price_rupees: float) -> None:
        """Update the net position (weighted-average cost) after a fill.

        `signed_qty_lots` is positive for a buy and negative for a sell. Handles
        adds, reductions and direction flips through zero.
        """
        if signed_qty_lots == 0:
            return

        old_qty = self.qty_lots
        same_direction_or_flat = old_qty == 0 or (old_qty > 0) == (signed_qty_lots > 0)

        if same_direction_or_flat:
            new_qty = old_qty + signed_qty_lots
            total_notional = self.avg_entry_price_rupees * abs(old_qty) + fill_price_rupees * abs(signed_qty_lots)
            self.avg_entry_price_rupees = total_notional / abs(new_qty) if new_qty else 0.0
            self.qty_lots = new_qty
            return

        closing_qty = min(abs(signed_qty_lots), abs(old_qty))
        direction = 1 if old_qty > 0 else -1
        self.realized_pnl_rupees += (
            closing_qty * self.lot_size * direction * (fill_price_rupees - self.avg_entry_price_rupees)
        )

        remaining_fill = abs(signed_qty_lots) - closing_qty
        qty_after_close = old_qty - direction * closing_qty

        if remaining_fill == 0:
            self.qty_lots = qty_after_close
            if self.qty_lots == 0:
                self.avg_entry_price_rupees = 0.0
            return

        new_direction = 1 if signed_qty_lots > 0 else -1
        self.qty_lots = new_direction * remaining_fill
        self.avg_entry_price_rupees = fill_price_rupees


@dataclass
class Book:
    legs: list[OptionLeg] = field(default_factory=list)
    futures: FuturesPosition | None = None

    def net_delta(self) -> float:
        total = sum(leg.delta_contribution() for leg in self.legs)
        if self.futures is not None:
            total += self.futures.delta_contribution()
        return total

    def net_gamma(self) -> float:
        return sum(leg.gamma_contribution() for leg in self.legs)

    def options_pnl(self) -> float:
        return sum(leg.pnl() for leg in self.legs)

    def futures_pnl(self) -> float:
        return self.futures.total_pnl() if self.futures is not None else 0.0

    def total_pnl(self) -> float:
        return self.options_pnl() + self.futures_pnl()

    def futures_lots(self) -> int:
        return self.futures.qty_lots if self.futures is not None else 0
