"""A paper-trading broker that fills against the live/simulated quote feed.

Safe by construction — it never touches a real market. Market orders fill at
the provider's current price; limit/stop orders rest as *working orders* until
:meth:`poll` finds the price has crossed their trigger. A buying-power check
(equity × max leverage) rejects orders the account can't support, so paper
trading behaves like a real margin account.
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
    WorkingOrder,
)


class PaperBroker:
    """In-memory broker with buying-power checks and working orders."""

    def __init__(
        self,
        provider,
        *,
        starting_cash: float = 100_000.0,
        currency: str = "USD",
        max_leverage: float = 1.0,
    ) -> None:
        self._provider = provider
        self._cash = starting_cash
        self._currency = currency
        self._max_leverage = max_leverage
        self._positions: dict[str, Position] = {}
        self._working: dict[str, WorkingOrder] = {}
        self._next_id = 1

    @property
    def name(self) -> str:
        return "Paper"

    @property
    def is_live(self) -> bool:
        return False

    # -- pricing --------------------------------------------------------------

    def _price_for(self, symbol: str) -> float | None:
        for inst in self._provider.instruments():
            if inst.symbol == symbol or inst.uid == symbol:
                q = self._provider.quote(inst.uid)
                return q.price if q else None
        return None

    # -- account --------------------------------------------------------------

    def positions(self) -> list[Position]:
        return list(self._positions.values())

    def working_orders(self) -> list[WorkingOrder]:
        return list(self._working.values())

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

    def _open_notional(self) -> float:
        total = 0.0
        for pos in self._positions.values():
            price = self._price_for(pos.symbol) or pos.entry_price
            total += abs(pos.quantity) * price
        return total

    def buying_power(self) -> float:
        """Equity × leverage minus notional already deployed."""
        return self.account().equity * self._max_leverage - self._open_notional()

    # -- orders ---------------------------------------------------------------

    def _new_id(self, prefix: str = "P") -> str:
        oid = f"{prefix}{self._next_id}"
        self._next_id += 1
        return oid

    def place_order(self, request: OrderRequest) -> OrderResult:
        price = self._price_for(request.symbol)
        if price is None:
            return OrderResult(False, message=f"No price for {request.symbol}")

        if request.order_type is OrderType.MARKET:
            return self._fill_market(request, price)

        # Limit / stop -> rest as a working order.
        if request.limit_price is None or request.limit_price <= 0:
            return OrderResult(False, message="Limit/stop orders need a price")
        oid = self._new_id("W")
        self._working[oid] = WorkingOrder(
            order_id=oid,
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            order_type=request.order_type,
            price=request.limit_price,
        )
        return OrderResult(True, order_id=oid, working=True, message="working")

    def _fill_market(self, request: OrderRequest, price: float) -> OrderResult:
        # Buying-power check only applies to orders that *increase* exposure.
        existing = self._positions.get(request.symbol)
        increases = existing is None or (
            (existing.side is Side.BUY) == (request.side is Side.BUY)
        )
        if increases:
            notional = request.quantity * price
            if notional > self.buying_power() + 1e-6:
                return OrderResult(
                    False,
                    message=(
                        f"Insufficient buying power: need {notional:,.0f}, "
                        f"have {self.buying_power():,.0f}"
                    ),
                )

        signed = request.quantity if request.side is Side.BUY else -request.quantity
        if existing is None:
            self._positions[request.symbol] = Position(
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                entry_price=price,
            )
        else:
            self._merge(existing, signed, price, request.symbol)

        return OrderResult(
            True, order_id=self._new_id(), filled_price=price, message="filled (paper)"
        )

    def _merge(self, existing: Position, signed_qty: float, price: float, symbol: str) -> None:
        cur_signed = existing.quantity if existing.side is Side.BUY else -existing.quantity
        net = cur_signed + signed_qty
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

    def poll(self) -> list[str]:
        """Fill any working orders whose trigger price has been crossed."""
        filled: list[str] = []
        for oid, order in list(self._working.items()):
            price = self._price_for(order.symbol)
            if price is None:
                continue
            if self._triggered(order, price):
                result = self._fill_market(
                    OrderRequest(order.symbol, order.side, order.quantity), price
                )
                if result.ok:
                    del self._working[oid]
                    filled.append(oid)
        return filled

    @staticmethod
    def _triggered(order: WorkingOrder, price: float) -> bool:
        buy = order.side is Side.BUY
        if order.order_type is OrderType.LIMIT:
            return price <= order.price if buy else price >= order.price
        if order.order_type is OrderType.STOP:
            return price >= order.price if buy else price <= order.price
        return False

    def cancel_order(self, order_id: str) -> OrderResult:
        if order_id in self._working:
            del self._working[order_id]
            return OrderResult(True, order_id=order_id, message="cancelled")
        return OrderResult(False, message=f"No working order {order_id}")

    def close_position(self, symbol: str) -> OrderResult:
        pos = self._positions.get(symbol)
        if pos is None:
            return OrderResult(False, message=f"No open position in {symbol}")
        opposite = Side.SELL if pos.side is Side.BUY else Side.BUY
        return self.place_order(OrderRequest(symbol=symbol, side=opposite, quantity=pos.quantity))


# Static type check: PaperBroker satisfies the Broker protocol.
_: type[Broker] = PaperBroker
