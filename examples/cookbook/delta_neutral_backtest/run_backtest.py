"""Backtest a short ATM straddle with and without a futures delta hedge on historical 1-minute data.

Type: read-only (fetches historical data only; never places orders)
Needs: login via PHONE_NO / MPIN in .env (env_creds=True); historical option data for the
       chosen dates (expired contracts are often missing on UAT; PROD has the full history)
Expect: per expiry, an unhedged vs hedged P&L comparison, then totals; CSVs under output/.
        Expiries with no data are reported as skipped.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import argparse
import sys

import pandas as pd
from nubra_python_sdk.start_sdk import NubraEnv

from backtest import engine, report, symbols
from backtest.data import HistoricalData, ist_to_utc

WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--underlying", default="NIFTY", help="index symbol (default NIFTY)")
    p.add_argument("--start", required=True, help="first date, YYYY-MM-DD (expiries on/after this date)")
    p.add_argument("--end", required=True, help="last date, YYYY-MM-DD (expiries on/before this date)")
    p.add_argument("--expiry-weekday", choices=WEEKDAYS, default="tue", help="weekly expiry weekday (default tue)")
    p.add_argument("--lot-size", type=int, default=65, help="contract lot size; check the instrument master")
    p.add_argument("--strike-step", type=int, default=50, help="strike spacing used to pick the ATM strike")
    p.add_argument("--entry-time", default="09:20", help="entry time IST on the day before expiry (HH:MM)")
    p.add_argument("--delta-threshold", type=float, default=0.5, help="rebalance when |net delta| > this many lots")
    p.add_argument("--max-futures-lots", type=int, default=20, help="cap on futures position, in lots")
    p.add_argument("--fee-per-lot", type=float, default=5.0, help="assumed fee per futures lot traded (Rs)")
    p.add_argument("--confirmation-bars", type=int, default=1, help="consecutive breach bars required before hedging")
    p.add_argument("--cooldown-minutes", type=float, default=0.0, help="block opposite-direction hedges for N minutes")
    p.add_argument("--cooldown-override", type=float, default=2.0,
                   help="breach multiple of the threshold that overrides the cooldown")
    p.add_argument("--stop-loss-multiple", type=float, default=None,
                   help="close everything once option P&L <= -multiple x premium collected (default: off)")
    p.add_argument("--env", choices=("uat", "prod"), default="uat", help="Nubra environment (default uat)")
    p.add_argument("--cache-dir", default=None, help="optional CSV cache directory, e.g. cache")
    p.add_argument("--output-dir", default="output", help="where to write CSV results (default output)")
    return p.parse_args(argv)


def build_expiry_data(md: HistoricalData, args, expiry: pd.Timestamp):
    weekday = WEEKDAYS[args.expiry_weekday]
    entry_day = symbols.entry_day_for(expiry)
    hh, mm = (int(x) for x in args.entry_time.split(":"))
    day_start, day_end = ist_to_utc(entry_day, 9, 15), ist_to_utc(expiry, 15, 30)
    entry_time = ist_to_utc(entry_day, hh, mm)

    index_df = md.index_bars(args.underlying, day_start, day_end)
    if index_df is None or index_df.empty:
        return None, "no index bars"
    before = index_df[index_df.index <= entry_time]
    if before.empty:
        return None, "no index bar at or before entry time"
    strike = symbols.round_to_strike_step(float(before["close"].iloc[-1]), args.strike_step)

    ce_sym = symbols.option_symbol(args.underlying, expiry, strike, "CE")
    pe_sym = symbols.option_symbol(args.underlying, expiry, strike, "PE")
    opts = md.option_bars([ce_sym, pe_sym], day_start, day_end)
    if opts.get(ce_sym) is None or opts.get(pe_sym) is None:
        return None, f"no option data for {ce_sym} / {pe_sym}"

    fut_sym, _ = symbols.front_futures(args.underlying, expiry, weekday)
    fut_df = md.futures_bars(fut_sym, day_start, day_end)
    if fut_df is None or fut_df.empty:
        return None, f"no futures data for {fut_sym}"

    data = engine.ExpiryData(label=str(expiry.date()), entry_time=entry_time, expiry_time=day_end,
                             strike=strike, ce=opts[ce_sym], pe=opts[pe_sym], fut=fut_df, index=index_df)
    return data, None


def main(argv=None):
    args = parse_args(argv)
    cfg = engine.HedgeConfig(
        lot_size=args.lot_size, delta_threshold_lots=args.delta_threshold, max_futures_lots=args.max_futures_lots,
        fee_per_lot=args.fee_per_lot, stop_loss_multiple=args.stop_loss_multiple,
        confirmation_bars=args.confirmation_bars, cooldown_minutes=args.cooldown_minutes,
        cooldown_override_multiple=args.cooldown_override)

    expiries = symbols.expiries_between(pd.Timestamp(args.start), pd.Timestamp(args.end),
                                        WEEKDAYS[args.expiry_weekday])
    if not expiries:
        sys.exit("No expiry dates fall inside the requested range.")

    # UAT by default. To use production, switch to NubraEnv.PROD (or pass --env prod).
    md = HistoricalData(NubraEnv.UAT if args.env == "uat" else NubraEnv.PROD, cache_dir=args.cache_dir)
    print(f"{args.underlying}: {len(expiries)} expiries, lot size {cfg.lot_size}, hedge threshold "
          f"{cfg.delta_threshold_lots} lots, env {args.env.upper()}")

    results = []
    for expiry in expiries:
        data, reason = build_expiry_data(md, args, expiry)
        if data is None:
            print(f"\nExpiry {expiry.date()}: skipped ({reason})")
            continue
        try:
            runs = {"unhedged": engine.run(data, cfg, hedged=False, label="Unhedged"),
                    "hedged": engine.run(data, cfg, hedged=True, label="Hedged")}
        except RuntimeError as exc:
            print(f"\nExpiry {expiry.date()}: skipped ({exc})")
            continue
        print(f"\nExpiry {data.label}  strike {data.strike}  premium collected "
              f"{report.rupees(runs['hedged'].premium_collected)}")
        report.print_run(runs["unhedged"])
        report.print_run(runs["hedged"])
        results.append((data, runs))

    if not results:
        sys.exit("\nNo expiry had complete data. Try --env prod or a more recent date range.")
    print("\nTotals")
    report.print_totals(results)
    report.write_outputs(results, args.output_dir)


if __name__ == "__main__":
    main()
