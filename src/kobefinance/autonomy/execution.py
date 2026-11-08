from __future__ import annotations
from kobefinance.services.trading.broker import OrderRequest,Side
from kobefinance.services.trading.paper_broker import PaperBroker
class AutonomousBrokerAdapter:
    def __init__(self,broker):
        if not isinstance(broker, PaperBroker):
            raise TypeError('Autonomous execution requires a paper broker')
        self.broker=broker
    def execute_autonomous(self,symbol,decision,approval):
        if not approval.approved or decision.action not in {'LONG', 'SHORT', 'HOLD', 'REDUCE', 'CLOSE'}:
            return None
        pos=next((p for p in self.broker.positions() if p.symbol==symbol),None)
        if decision.action=='HOLD': return None
        if decision.action=='CLOSE': return self.broker.close_position(symbol) if pos else None
        acct=self.broker.account(); price=getattr(self.broker,'_price_for',lambda s:None)(symbol)
        if not price: return None
        max_notional=max(0.,acct.equity*approval.max_position_pct); qty=max_notional/price
        if decision.action=='REDUCE':
            if not pos:return None
            side=Side.SELL if pos.side is Side.BUY else Side.BUY
            return self.broker.place_order(OrderRequest(symbol,side,pos.quantity*.5,comment='Kobe autonomous reduce'))
        side=Side.BUY if decision.action=='LONG' else Side.SELL
        if pos and pos.side is not side:self.broker.close_position(symbol)
        return self.broker.place_order(OrderRequest(symbol,side,qty,comment='Kobe autonomous MVP'))
