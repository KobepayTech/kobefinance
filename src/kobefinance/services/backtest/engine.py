"""A long/short backtest engine over a Candle series.

Full-equity allocation: each entry deploys the current equity into one
position; closing realizes it back to cash. Produces an equity curve, the
list of round-trip trades, and summary metrics (return, Sharpe, max drawdown,
win rate).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ...models import Candle
from .strategy import Context, Strategy

_BARS_PER_YEAR = 252.0  # daily series annualization factor


@dataclass(frozen=True)
class Trade:
    entry_ts: int
    exit_ts: int
    side: str          # "long" | "short"
    entry_price: float
    exit_price: float
    return_pct: float


@dataclass
class BacktestResult:
    equity_curve: list[tuple[int, float]] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


def run_backtest(
    candles: list[Candle], strategy: Strategy, *, starting_cash: float = 10_000.0
) -> BacktestResult:
    """Run *strategy* over *candles* and return the result."""
    closes = [c.close for c in candles]
    strategy.prepare(closes)

    cash = starting_cash
    position = 0          # 1 long, -1 short, 0 flat
    units = 0.0
    entry_price = 0.0
    entry_ts = 0
    trades: list[Trade] = []
    equity_curve: list[tuple[int, float]] = []

    def equity_at(price: float) -> float:
        if position == 1:
            return cash + units * price
        if position == -1:
            return cash - units * price  # short liability
        return cash

    for candle in candles:
        price = candle.close
        ctx = Context(index=len(equity_curve), price=price, position=position)
        strategy.on_bar(ctx)
        action = ctx.action

        want = {"buy": 1, "sell": -1, "close": 0}.get(action) if action else None
        if want is not None and want != position:
            # Close any existing position first, realizing the trade.
            if position != 0:
                exit_value = units * price
                if position == 1:
                    cash += exit_value
                    ret = (price - entry_price) / entry_price * 100.0
                    side = "long"
                else:
                    cash -= exit_value  # buy back the short
                    ret = (entry_price - price) / entry_price * 100.0
                    side = "short"
                trades.append(Trade(entry_ts, candle.ts, side, entry_price, price, ret))
                units = 0.0
                position = 0
            # Open the new position with full current equity.
            if want != 0 and price > 0:
                notional = equity_at(price)
                units = notional / price
                entry_price = price
                entry_ts = candle.ts
                if want == 1:
                    cash -= notional
                else:  # short: receive proceeds
                    cash += notional
                position = want

        equity_curve.append((candle.ts, equity_at(price)))

    metrics = _metrics(equity_curve, trades, starting_cash)
    return BacktestResult(equity_curve=equity_curve, trades=trades, metrics=metrics)


def _metrics(
    equity_curve: list[tuple[int, float]], trades: list[Trade], starting_cash: float
) -> dict[str, float]:
    if not equity_curve:
        return {}
    equities = [e for _, e in equity_curve]
    final = equities[-1]
    total_return = (final - starting_cash) / starting_cash * 100.0

    # Max drawdown.
    peak = equities[0]
    max_dd = 0.0
    for e in equities:
        peak = max(peak, e)
        if peak > 0:
            max_dd = min(max_dd, (e - peak) / peak * 100.0)

    # Sharpe from per-bar returns.
    rets = [
        (equities[i] - equities[i - 1]) / equities[i - 1]
        for i in range(1, len(equities))
        if equities[i - 1] > 0
    ]
    sharpe = 0.0
    if len(rets) > 1:
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        std = math.sqrt(var)
        if std > 0:
            sharpe = (mean / std) * math.sqrt(_BARS_PER_YEAR)

    wins = [t for t in trades if t.return_pct > 0]
    win_rate = (len(wins) / len(trades) * 100.0) if trades else 0.0
    avg_trade = (sum(t.return_pct for t in trades) / len(trades)) if trades else 0.0

    return {
        "total_return_pct": round(total_return, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe": round(sharpe, 2),
        "num_trades": float(len(trades)),
        "win_rate_pct": round(win_rate, 2),
        "avg_trade_pct": round(avg_trade, 2),
        "final_equity": round(final, 2),
    }
