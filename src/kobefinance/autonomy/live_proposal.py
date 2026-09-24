from __future__ import annotations
from dataclasses import dataclass
from kobefinance.services.trading.broker import OrderRequest,Side
@dataclass(frozen=True)
class LiveOrderProposal:
    request:OrderRequest; confidence:float; reason:str; risk_reason:str
class LiveProposalBuilder:
    """Builds a fully-sized live order proposal. Submission remains an explicit broker action."""
    def build(self,symbol,decision,approval,equity,price):
        if not approval.approved or decision.action not in ('LONG','SHORT') or price<=0:return None
        qty=(max(0.,float(equity))*approval.max_position_pct)/float(price)
        side=Side.BUY if decision.action=='LONG' else Side.SELL
        return LiveOrderProposal(OrderRequest(symbol,side,qty,comment='Kobe autonomous proposal'),decision.confidence,decision.reason,approval.reason)
