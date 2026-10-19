"""Offline checks for the hedge maths, the replay and the order safety flags (no login, no network).

Run from the delta_hedging folder:  python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hedging import logic  # noqa: E402
from hedging.backtest import BacktestConfig, Bar, align_bars, simulate, to_utc_iso  # noqa: E402
from hedging.session import check_order_flags  # noqa: E402
from hedging.state import PositionState  # noqa: E402


class HedgeMath(unittest.TestCase):
    def test_net_delta_and_order_direction(self):
        # long 1 lot (100 sh) future, short 2 calls of 100 sh at delta 0.5 -> flat
        net = logic.compute_net_delta_shares(100, [0.5, 0.5], [100, 100], 0)
        self.assertAlmostEqual(net, 0.0)
        self.assertIsNone(logic.compute_hedge_order(net))
        # delta rises to 0.6: net = 100 - 120 = -20 -> BUY 20 shares
        net = logic.compute_net_delta_shares(100, [0.6, 0.6], [100, 100], 0)
        self.assertEqual(logic.compute_hedge_order(net), ("BUY", 20))
        # delta falls to 0.4: net = +20 -> SELL 20 shares
        net = logic.compute_net_delta_shares(100, [0.4, 0.4], [100, 100], 0)
        self.assertEqual(logic.compute_hedge_order(net), ("SELL", 20))

    def test_rehedge_trigger_and_exit(self):
        self.assertFalse(logic.should_check_rehedge(100.0, 101.0, 1.5))
        self.assertTrue(logic.should_check_rehedge(100.0, 101.5, 1.5))
        self.assertTrue(logic.should_check_rehedge(0.0, 100.0, 1.5))
        self.assertTrue(logic.evaluate_exit(5000, 5000, -3000)[0])
        self.assertTrue(logic.evaluate_exit(-3000, 5000, -3000)[0])
        self.assertFalse(logic.evaluate_exit(0, 5000, -3000)[0])

    def test_atm_selection(self):
        self.assertEqual(logic.select_atm_call_index([90, 100, 110], [0.8, 0.52, 0.2], 100), 1)
        self.assertEqual(logic.select_atm_call_index([90, 100, 110], None, 108), 2)

    def test_hedge_fill_bookkeeping(self):
        shares, avg, realized = logic.apply_hedge_fill(
            prev_shares=0, avg_hedge_price=0, realized_pnl=0, side="BUY", qty=10, fill_price=100)
        self.assertEqual((shares, avg, realized), (10, 100, 0))
        shares, avg, realized = logic.apply_hedge_fill(
            prev_shares=shares, avg_hedge_price=avg, realized_pnl=realized, side="SELL", qty=4, fill_price=110)
        self.assertEqual((shares, avg, realized), (6, 100, 40))

    def test_state_uses_same_bookkeeping(self):
        s = PositionState(symbol="TEST")
        s.record_hedge_trade(timestamp="t", side="SELL", qty=10, price=100.0, underlying_price=100.0,
                             net_delta_before=10, net_delta_after=0)
        self.assertEqual(s.equity_hedge_shares, -10)
        s.record_hedge_trade(timestamp="t", side="BUY", qty=10, price=90.0, underlying_price=90.0,
                             net_delta_before=-10, net_delta_after=0)
        self.assertEqual(s.equity_hedge_shares, 0)
        self.assertAlmostEqual(s.cumulative_hedge_realized_pnl, 100.0)


class Replay(unittest.TestCase):
    def cfg(self, **kw):
        base = dict(future_symbol="F", call_symbol="C", equity_symbol="E", lot_size=100,
                    pnl_target=5000, pnl_stop_loss=-3000, start_date="2025-01-01", end_date="2025-01-02")
        base.update(kw)
        return BacktestConfig(**base)

    def bars(self, rows):
        return [Bar(i * 1_000_000_000, f, c, d, e) for i, (f, c, d, e) in enumerate(rows)]

    def test_hedge_then_target_exit(self):
        bars = self.bars([
            (100.0, 5.0, 0.50, 100.0),
            (102.0, 6.0, 0.60, 102.0),   # +2% move: re-hedge (net delta -20 -> BUY 20)
            (110.0, 8.0, 0.60, 110.0),
            (160.0, 9.0, 0.60, 160.0),   # large move -> PnL target reached
        ])
        res = simulate(bars, self.cfg())
        self.assertEqual(len(res.trades), 1)
        self.assertEqual((res.trades[0].side, res.trades[0].qty), ("BUY", 20))
        self.assertAlmostEqual(res.trades[0].net_delta_after, 0.0)
        self.assertFalse(res.unresolved)
        self.assertTrue(res.target_hit)

    def test_unresolved_window(self):
        bars = self.bars([(100.0, 5.0, 0.5, 100.0), (100.1, 5.0, 0.5, 100.1)])
        res = simulate(bars, self.cfg())
        self.assertTrue(res.unresolved)
        self.assertEqual(res.trades, [])

    def test_align_and_dates(self):
        bars = align_bars({1: 1.0, 2: 2.0}, {1: 1.0, 2: 2.0}, {2: 0.5}, {1: 1.0, 2: 2.0})
        self.assertEqual([b.timestamp_ns for b in bars], [2])
        self.assertEqual(to_utc_iso("2025-08-01"), "2025-08-01T03:45:00.000Z")
        self.assertEqual(to_utc_iso("2025-08-29", end_of_session=True), "2025-08-29T10:00:00.000Z")

    def test_config_validation(self):
        with self.assertRaises(SystemExit):
            self.cfg(pnl_stop_loss=100).validate()


class OrderSafety(unittest.TestCase):
    def test_prod_needs_second_flag(self):
        with self.assertRaises(SystemExit):
            check_order_flags("prod", place_orders=True, allow_prod=False)
        check_order_flags("prod", place_orders=True, allow_prod=True)
        check_order_flags("prod", place_orders=False, allow_prod=False)  # dry run is fine
        check_order_flags("uat", place_orders=True, allow_prod=False)


if __name__ == "__main__":
    unittest.main()
