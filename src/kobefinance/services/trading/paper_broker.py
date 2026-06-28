"""A paper-trading broker that fills against the live/simulated quote feed.

Safe by construction — it never touches a real market. Market orders fill at
the provider's current price for the instrument; positions net against each
other per symbol. This is the default broker everywhere and the execution
venue for backtested bots promoted to "live" paper trading.
"""

from __future__ import annotations

from .broker import (
    Account,
    Broker,
    OrderRequest,
    OrderResult,
    OrderType,
    Position,
    Side,
)


class PaperBroker:
    """In-memory broker; fills market orders at the feed's current price."""

    def __init__(self, provider, *, starting_cash: float = 100_000.0, currency: str = "USD") -> None:
        self._provider = provider
        self._cash = starting_cash
        self._currency = currency
        self._positions: dict[str, Position] = {}
        self._next_id = 1

    @property
    def name(self) -> str:
        return "Paper"

    @property
    def is_live(self) -> bool:
        return False

    # -- pricing --------------------------------------------------------------

    def _price_for(self, symbol: str) -> float | None:
        """Resolve a broker symbol to a current price via the data provider."""
        # Accept either a bare symbol or a full uid; match the first instrument.
        for inst in self._provider.instruments():
            if inst.symbol == symbol or inst.uid == symbol:
                q = self._provider.quote(inst.uid)
                return q.price if q else None
        return None

    # -- account --------------------------------------------------------------

    def positions(self) -> list[Position]:
        return list(self._positions.values())

    def account(self) -> Account:
        equity = self._cash
        for pos in self._positions.values():
            price = self._price_for(pos.symbol)
            if price is not None:
                equity += pos.unrealized_pnl(price)
        return Account(
            currency=self._currency,
            balance=round(self._cash, 2),
            equity=round(equity, 2),
            positions=self.positions(),
        )

    # -- orders ---------------------------------------------------------------

    def place_order(self, request: OrderRequest) -> OrderResult:
        if request.order_type is not OrderType.MARKET:
            return OrderResult(False, message="Paper broker supports market orders only")
        price = self._price_for(request.symbol)
        if price is None:
            return OrderResult(False, message=f"No price for {request.symbol}")

        signed = request.quantity if request.side is Side.BUY else -request.quantity
        existing = self._positions.get(request.symbol)
        if existing is None:
            self._positions[request.symbol] = Position(
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                entry_price=price,
            )
        else:
            self._merge(existing, signed, price, request.symbol)

        order_id = f"P{self._next_id}"
        self._next_id += 1
        return OrderResult(True, order_id=order_id, filled_price=price, message="filled (paper)")

    def _merge(self, existing: Position, signed_qty: float, price: float, symbol: str) -> None:
        cur_signed = existing.quantity if existing.side is Side.BUY else -existing.quantity
        net = cur_signed + signed_qty
        # Realize PnL on the portion that closed.
        closing = min(abs(cur_signed), abs(signed_qty)) if (cur_signed * signed_qty) < 0 else 0.0
        if closing:
            self._cash += existing.unrealized_pnl(price) * (closing / abs(cur_signed))
        if abs(net) < 1e-9:
            del self._positions[symbol]
        else:
            self._positions[symbol] = Position(
                symbol=symbol,
                side=Side.BUY if net > 0 else Side.SELL,
                quantity=abs(net),
                entry_price=price if (cur_signed * net) <= 0 else existing.entry_price,
            )

    def close_position(self, symbol: str) -> OrderResult:
        pos = self._positions.get(symbol)
        if pos is None:
            return OrderResult(False, message=f"No open position in {symbol}")
        opposite = Side.SELL if pos.side is Side.BUY else Side.BUY
        return self.place_order(
            OrderRequest(symbol=symbol, side=opposite, quantity=pos.quantity)
        )


# Static type check: PaperBroker satisfies the Broker protocol.
_: type[Broker] = PaperBroker
