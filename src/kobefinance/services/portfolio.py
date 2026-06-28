"""Portfolio analytics: holdings, allocation, and risk metrics.

Reads open positions from a broker and prices/history from the data provider,
then derives allocation weights and portfolio-level risk (annualized
volatility, Sharpe, max drawdown, and historical 1-day 95% VaR) from a
weighted blend of each holding's return series.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

_BARS_PER_YEAR = 252.0


@dataclass(frozen=True)
class Holding:
    symbol: str
    side: str
    quantity: float
    entry_price: float
    price: float
    market_value: float
    weight_pct: float
    unrealized_pnl: float


@dataclass
class PortfolioSnapshot:
    holdings: list[Holding] = field(default_factory=list)
    total_value: float = 0.0
    risk: dict[str, float] = field(default_factory=dict)


def _uid_for(provider, symbol: str) -> str | None:
    for inst in provider.instruments():
        if inst.symbol == symbol or inst.uid == symbol:
            return inst.uid
    return None


def _returns(closes: list[float]) -> list[float]:
    return [
        (closes[i] - closes[i - 1]) / closes[i - 1]
        for i in range(1, len(closes))
        if closes[i - 1] > 0
    ]


def build_snapshot(broker, provider, *, range_key: str = "6M") -> PortfolioSnapshot:
    """Compute the current portfolio snapshot from broker positions."""
    positions = broker.positions()
    priced: list[tuple] = []
    total = 0.0
    for pos in positions:
        uid = _uid_for(provider, pos.symbol)
        quote = provider.quote(uid) if uid else None
        price = quote.price if quote else pos.entry_price
        mv = abs(pos.quantity) * price
        total += mv
        priced.append((pos, uid, price, mv))

    holdings: list[Holding] = []
    for pos, _uid, price, mv in priced:
        holdings.append(
            Holding(
                symbol=pos.symbol,
                side=pos.side.value,
                quantity=pos.quantity,
                entry_price=pos.entry_price,
                price=price,
                market_value=round(mv, 2),
                weight_pct=round(mv / total * 100.0, 2) if total else 0.0,
                unrealized_pnl=round(pos.unrealized_pnl(price), 2),
            )
        )
    holdings.sort(key=lambda h: h.market_value, reverse=True)

    risk = _risk(priced, total, provider, range_key)
    return PortfolioSnapshot(holdings=holdings, total_value=round(total, 2), risk=risk)


def _risk(priced, total: float, provider, range_key: str) -> dict[str, float]:
    if not priced or total <= 0:
        return {}

    # Per-holding return series, weighted by market value.
    series: list[tuple[float, list[float]]] = []  # (weight, returns)
    for pos, uid, _price, mv in priced:
        if uid is None:
            continue
        closes = [c.close for c in provider.history(uid, range_key)]
        rets = _returns(closes)
        if rets:
            # Short positions invert the return contribution.
            sign = 1.0 if pos.side.value == "buy" else -1.0
            series.append((mv / total, [sign * r for r in rets]))
    if not series:
        return {}

    n = min(len(r) for _, r in series)
    if n < 2:
        return {}
    port = [sum(w * r[len(r) - n + i] for w, r in series) for i in range(n)]

    mean = sum(port) / n
    var = sum((r - mean) ** 2 for r in port) / (n - 1)
    std = math.sqrt(var)
    ann_vol = std * math.sqrt(_BARS_PER_YEAR) * 100.0
    sharpe = (mean / std * math.sqrt(_BARS_PER_YEAR)) if std > 0 else 0.0

    # Max drawdown of the cumulative portfolio return.
    cum = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in port:
        cum *= 1.0 + r
        peak = max(peak, cum)
        max_dd = min(max_dd, (cum - peak) / peak)

    # Historical 1-day 95% VaR (loss) in currency.
    ordered = sorted(port)
    idx = max(0, int(0.05 * len(ordered)) - 1)
    var_pct = -ordered[idx] * 100.0
    var_cash = max(0.0, -ordered[idx]) * total

    return {
        "annual_vol_pct": round(ann_vol, 2),
        "sharpe": round(sharpe, 2),
        "max_drawdown_pct": round(max_dd * 100.0, 2),
        "var95_pct": round(var_pct, 2),
        "var95_cash": round(var_cash, 2),
    }
