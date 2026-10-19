"""Short ATM straddle with an optional futures delta hedge, simulated on 1-minute bars.

Pure logic: no network, no SDK. Feed it an `ExpiryData` built from historical
bars (see data.py / run_backtest.py) and it returns a `RunResult`.

Position: sell 1 lot CE + 1 lot PE at the same strike and expiry, at the entry
minute's mid price ((bid + ask) / 2). Exit: cash-settled at the expiry-day close
using the index close as the settlement proxy (not the exchange's official
settlement average). The option legs are never adjusted.

Hedge (hedge=True):
  net_delta = sum(-leg_delta) * lot_size + futures_lots * lot_size
  net_gamma = sum(-leg_gamma) * lot_size                      (reported only)
  rebalance condition: |net_delta| > delta_threshold_lots * lot_size
  trade size: -round(net_delta / lot_size) lots of futures, clamped so that
              |position| <= max_futures_lots
  Fills: buys pay the ask, sells receive the bid, plus fee_per_lot per lot.
  The condition is evaluated once per 1-minute bar, so intra-minute
  rebalancing is not modelled.

Optional rebalance-policy filters (both off by default):
  confirmation_bars  breach must persist this many consecutive bars before a trade
  cooldown_minutes   block a trade in the opposite direction of the previous one for
                     this long, unless |net_delta| exceeds cooldown_override_multiple
                     times the threshold
Optional exit rule: stop_loss_multiple closes the option legs (at mid) and any
futures (at bid/ask) once option P&L <= -multiple * premium collected.

Every price is in rupees; P&L is in rupees for the whole position.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class HedgeConfig:
    lot_size: int = 65
    delta_threshold_lots: float = 0.5
    max_futures_lots: int = 20
    fee_per_lot: float = 5.0                  # flat fee per futures lot traded (assumption)
    gamma_flag_threshold: float = 0.20        # only counts bars with |net_gamma| above this
    stop_loss_multiple: float | None = None   # e.g. 1.5; None disables the stop
    confirmation_bars: int = 1
    cooldown_minutes: float = 0.0
    cooldown_override_multiple: float = 2.0


@dataclass
class ExpiryData:
    label: str
    entry_time: pd.Timestamp     # naive UTC
    expiry_time: pd.Timestamp    # naive UTC (expiry-day close)
    strike: int
    ce: pd.DataFrame             # indexed by time: close, bid, ask, delta, gamma
    pe: pd.DataFrame
    fut: pd.DataFrame            # indexed by time: close, bid, ask
    index: pd.DataFrame          # indexed by time: close (settlement proxy)


@dataclass
class HedgeTrade:
    time: pd.Timestamp
    lots: int                    # signed: +buy, -sell
    exec_price: float
    mid_price: float
    fee: float
    net_delta_before: float
    net_gamma_before: float
    position_after: int
    reason: str                  # immediate | confirmed | cooldown_override | expiry_close | stop_close


@dataclass
class RunResult:
    label: str
    hedged: bool
    lot_size: int
    premium_collected: float
    times: list = field(default_factory=list)
    pnl_path: list = field(default_factory=list)         # net P&L (bid/ask fills + fees)
    gross_pnl_path: list = field(default_factory=list)   # same trades filled at mid, no fees
    net_delta_path: list = field(default_factory=list)
    net_gamma_path: list = field(default_factory=list)
    trades: list = field(default_factory=list)
    high_gamma_bars: int = 0
    final_pnl: float = 0.0
    final_gross_pnl: float = 0.0
    ce_settle: float | None = None
    pe_settle: float | None = None
    stopped_out: bool = False
    breach_bars: int = 0
    confirmation_blocked_bars: int = 0
    cooldown_blocked_bars: int = 0
    rounds_to_zero_bars: int = 0

    @property
    def total_fees(self) -> float:
        return sum(t.fee for t in self.trades)

    @property
    def slippage_cost(self) -> float:
        return sum(abs(t.exec_price - t.mid_price) * abs(t.lots) * self.lot_size for t in self.trades)

    @property
    def hedging_cost(self) -> float:
        return self.final_gross_pnl - self.final_pnl

    @property
    def max_drawdown(self) -> float:
        peak, worst = -float("inf"), 0.0
        for p in self.pnl_path:
            peak = max(peak, p)
            worst = max(worst, peak - p)
        return worst

    @property
    def worst_pnl(self) -> float:
        return min(self.pnl_path) if self.pnl_path else 0.0

    @property
    def max_abs_net_delta(self) -> float:
        return max((abs(d) for d in self.net_delta_path), default=0.0)

    def summary_row(self) -> dict:
        return {
            "label": self.label, "hedged": self.hedged, "premium_collected": round(self.premium_collected, 2),
            "final_pnl": round(self.final_pnl, 2), "final_pnl_before_hedge_cost": round(self.final_gross_pnl, 2),
            "hedge_trades": len([t for t in self.trades if t.reason not in ("expiry_close", "stop_close")]),
            "slippage_cost": round(self.slippage_cost, 2), "fees": round(self.total_fees, 2),
            "max_drawdown": round(self.max_drawdown, 2), "worst_pnl": round(self.worst_pnl, 2),
            "max_abs_net_delta": round(self.max_abs_net_delta, 2), "stopped_out": self.stopped_out,
        }


def _aligned(data: ExpiryData, times: pd.DatetimeIndex) -> pd.DataFrame:
    """Last-known value of every series as of each bar time (forward fill)."""
    def col(df, name):
        return df[name].dropna().reindex(df[name].dropna().index.union(times)).ffill().reindex(times)

    return pd.DataFrame({
        "ce_bid": col(data.ce, "bid"), "ce_ask": col(data.ce, "ask"),
        "pe_bid": col(data.pe, "bid"), "pe_ask": col(data.pe, "ask"),
        "ce_delta": col(data.ce, "delta"), "pe_delta": col(data.pe, "delta"),
        "ce_gamma": col(data.ce, "gamma"), "pe_gamma": col(data.pe, "gamma"),
        "fut_bid": col(data.fut, "bid"), "fut_ask": col(data.fut, "ask"),
        "spot": col(data.index, "close"),
    }, index=times)


def run(data: ExpiryData, cfg: HedgeConfig, hedged: bool, label: str) -> RunResult:
    lot = cfg.lot_size
    both = sorted(set(data.ce.index) & set(data.pe.index))
    times = pd.DatetimeIndex([t for t in both if t >= data.entry_time])
    if len(times) == 0:
        raise RuntimeError(f"{data.label}: no option bars at or after entry {data.entry_time}")
    a = _aligned(data, times)
    a["ce_mid"] = (a["ce_bid"] + a["ce_ask"]) / 2.0
    a["pe_mid"] = (a["pe_bid"] + a["pe_ask"]) / 2.0
    a["fut_mid"] = (a["fut_bid"] + a["fut_ask"]) / 2.0
    # Only bars where both legs have a mid price; the last of these is the expiry bar.
    a = a[a["ce_mid"].notna() & a["pe_mid"].notna()]
    if a.empty or pd.isna(a["ce_mid"].iloc[0]):
        raise RuntimeError(f"{data.label}: no CE/PE mid price at entry")
    ce0, pe0 = a["ce_mid"].iloc[0], a["pe_mid"].iloc[0]
    premium = (ce0 + pe0) * lot
    res = RunResult(label=label, hedged=hedged, lot_size=lot, premium_collected=premium)

    position = 0
    cash_net = cash_gross = 0.0
    streak = 0
    last_time = last_dir = None
    last_bar = a.index[-1]
    cooldown = pd.Timedelta(minutes=cfg.cooldown_minutes)

    for t, r in a.iterrows():
        is_last = t == last_bar
        if is_last:
            # Settlement proxy: last index close at or before the expiry-day close.
            closes = data.index["close"].dropna()
            closes = closes[closes.index <= data.expiry_time]
            spot = float(closes.iloc[-1]) if len(closes) else float(r["spot"])
            ce_mark, pe_mark = max(spot - data.strike, 0.0), max(data.strike - spot, 0.0)
            res.ce_settle, res.pe_settle = ce_mark, pe_mark
        else:
            ce_mark, pe_mark = r["ce_mid"], r["pe_mid"]
        option_pnl = -(ce_mark - ce0) * lot - (pe_mark - pe0) * lot

        net_delta = net_gamma = 0.0
        has_greeks = not (pd.isna(r["ce_delta"]) or pd.isna(r["pe_delta"]))
        if has_greeks:
            net_delta = (-r["ce_delta"] - r["pe_delta"]) * lot + position * lot
            if not (pd.isna(r["ce_gamma"]) or pd.isna(r["pe_gamma"])):
                net_gamma = (-r["ce_gamma"] - r["pe_gamma"]) * lot
        if abs(net_gamma) >= cfg.gamma_flag_threshold:
            res.high_gamma_bars += 1

        stop = (cfg.stop_loss_multiple is not None and not is_last
                and option_pnl <= -cfg.stop_loss_multiple * premium)
        if stop:
            res.stopped_out = True

        fut_ok = not pd.isna(r["fut_mid"])
        if hedged and not is_last and not stop and has_greeks and fut_ok:
            breach = abs(net_delta) > cfg.delta_threshold_lots * lot
            streak = streak + 1 if breach else 0
            if breach:
                res.breach_bars += 1
                lots = -round(net_delta / lot)
                if streak < cfg.confirmation_bars:
                    res.confirmation_blocked_bars += 1
                elif lots == 0:
                    res.rounds_to_zero_bars += 1
                else:
                    direction = 1 if lots > 0 else -1
                    override = abs(net_delta) > cfg.cooldown_override_multiple * cfg.delta_threshold_lots * lot
                    in_window = (cfg.cooldown_minutes > 0 and last_time is not None
                                 and (t - last_time) < cooldown and direction != last_dir)
                    if in_window and not override:
                        res.cooldown_blocked_bars += 1
                    else:
                        adaptive = cfg.confirmation_bars > 1 or cfg.cooldown_minutes > 0
                        reason = "cooldown_override" if (in_window and override) else (
                            "confirmed" if adaptive else "immediate")
                        lots = int(np.clip(position + lots, -cfg.max_futures_lots, cfg.max_futures_lots) - position)
                        if lots != 0:
                            price = r["fut_ask"] if lots > 0 else r["fut_bid"]
                            fee = cfg.fee_per_lot * abs(lots)
                            cash_net += -lots * price * lot - fee
                            cash_gross += -lots * r["fut_mid"] * lot
                            position += lots
                            res.trades.append(HedgeTrade(t, lots, price, r["fut_mid"], fee, net_delta,
                                                         net_gamma, position, reason))
                            last_time, last_dir, streak = t, direction, 0

        if (is_last or stop) and hedged and position != 0 and fut_ok:
            lots = -position
            price = r["fut_ask"] if lots > 0 else r["fut_bid"]
            fee = cfg.fee_per_lot * abs(lots)
            cash_net += -lots * price * lot - fee
            cash_gross += -lots * r["fut_mid"] * lot
            position = 0
            res.trades.append(HedgeTrade(t, lots, price, r["fut_mid"], fee, net_delta, net_gamma, 0,
                                         "stop_close" if stop else "expiry_close"))

        mark = 0.0 if pd.isna(r["fut_mid"]) else r["fut_mid"]
        res.times.append(t)
        # net_delta_path records the delta reached before this bar's hedge acted on it.
        res.pnl_path.append(option_pnl + cash_net + position * mark * lot)
        res.gross_pnl_path.append(option_pnl + cash_gross + position * mark * lot)
        res.net_delta_path.append(net_delta)
        res.net_gamma_path.append(net_gamma)
        if is_last or stop:
            break

    res.final_pnl, res.final_gross_pnl = res.pnl_path[-1], res.gross_pnl_path[-1]
    return res
