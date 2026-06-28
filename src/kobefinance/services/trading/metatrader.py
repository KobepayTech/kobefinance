"""MetaTrader 5 broker adapter (live forex/CFD trading).

The official ``MetaTrader5`` Python package is **Windows-only** and requires
the MT5 desktop terminal installed and logged in to a broker account. This
adapter imports it lazily, so the module is importable on any platform; when
the package or terminal is unavailable (e.g. this Linux container), the
adapter reports ``available is False`` and refuses to place orders rather than
pretending to trade.

Live order placement is real money. Callers should confirm with the user
before every live order and default to the paper broker otherwise.
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


def _load_mt5():
    """Return the MetaTrader5 module if importable, else ``None``."""
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception:
        return None
    return mt5


class MetaTraderBroker:
    """Routes orders to a locally running MetaTrader 5 terminal."""

    def __init__(self) -> None:
        self._mt5 = _load_mt5()
        self._connected = False

    @property
    def name(self) -> str:
        return "MetaTrader 5"

    @property
    def is_live(self) -> bool:
        return True

    @property
    def available(self) -> bool:
        """True only where the MT5 package imports (Windows + installed)."""
        return self._mt5 is not None

    # -- connection -----------------------------------------------------------

    def connect(
        self, login: int | None = None, password: str = "", server: str = ""
    ) -> OrderResult:
        """Initialize the terminal and (optionally) log in to an account."""
        if self._mt5 is None:
            return OrderResult(
                False,
                message="MetaTrader5 package unavailable (Windows + MT5 terminal required)",
            )
        ok = (
            self._mt5.initialize(login=login, password=password, server=server)
            if login is not None
            else self._mt5.initialize()
        )
        if not ok:
            return OrderResult(False, message=f"MT5 initialize failed: {self._mt5.last_error()}")
        self._connected = True
        return OrderResult(True, message="connected")

    def shutdown(self) -> None:
        if self._mt5 is not None and self._connected:
            self._mt5.shutdown()
            self._connected = False

    def _require(self) -> OrderResult | None:
        if self._mt5 is None:
            return OrderResult(False, message="MetaTrader5 package unavailable")
        if not self._connected:
            return OrderResult(False, message="Not connected — call connect() first")
        return None

    # -- account --------------------------------------------------------------

    def account(self) -> Account:
        if self._mt5 is None or not self._connected:
            return Account()
        info = self._mt5.account_info()
        if info is None:
            return Account()
        return Account(
            currency=info.currency,
            balance=info.balance,
            equity=info.equity,
            positions=self.positions(),
        )

    def positions(self) -> list[Position]:
        if self._mt5 is None or not self._connected:
            return []
        raw = self._mt5.positions_get() or []
        out: list[Position] = []
        for p in raw:
            side = Side.BUY if p.type == self._mt5.POSITION_TYPE_BUY else Side.SELL
            out.append(Position(p.symbol, side, p.volume, p.price_open))
        return out

    # -- orders ---------------------------------------------------------------

    def place_order(self, request: OrderRequest) -> OrderResult:
        guard = self._require()
        if guard is not None:
            return guard
        if request.order_type is not OrderType.MARKET:
            return OrderResult(False, message="This adapter places market orders only")

        mt5 = self._mt5
        tick = mt5.symbol_info_tick(request.symbol)
        if tick is None:
            return OrderResult(False, message=f"Unknown symbol {request.symbol}")
        is_buy = request.side is Side.BUY
        order = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": request.symbol,
            "volume": float(request.quantity),
            "type": mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
            "price": tick.ask if is_buy else tick.bid,
            "deviation": 20,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "type_time": mt5.ORDER_TIME_GTC,
            "comment": request.comment or "kobefinance",
        }
        result = mt5.order_send(order)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return OrderResult(False, message=f"order_send failed: {getattr(result, 'comment', result)}")
        return OrderResult(True, order_id=str(result.order), filled_price=result.price, message="filled")

    def close_position(self, symbol: str) -> OrderResult:
        guard = self._require()
        if guard is not None:
            return guard
        for pos in self.positions():
            if pos.symbol == symbol:
                opposite = Side.SELL if pos.side is Side.BUY else Side.BUY
                return self.place_order(
                    OrderRequest(symbol=symbol, side=opposite, quantity=pos.quantity, comment="close")
                )
        return OrderResult(False, message=f"No open position in {symbol}")


# Static type check: MetaTraderBroker satisfies the Broker protocol.
_: type[Broker] = MetaTraderBroker
