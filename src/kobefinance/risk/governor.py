from dataclasses import dataclass
@dataclass(frozen=True)
class RiskLimits:
    max_position_pct:float=.02; max_daily_loss_pct:float=.02; max_drawdown_pct:float=.10; max_leverage:float=1.; min_confidence:float=.55
@dataclass(frozen=True)
class RiskApproval:
    approved:bool; reason:str; max_position_pct:float=0.
class RiskGovernor:
    def __init__(self,limits=None): self.limits=limits or RiskLimits()
    def evaluate(self,state,decision):
        if float(state.get('daily_loss_pct',0))>=self.limits.max_daily_loss_pct:return RiskApproval(False,'daily loss limit')
        if float(state.get('drawdown_pct',0))>=self.limits.max_drawdown_pct:return RiskApproval(False,'drawdown kill switch')
        if float(state.get('leverage',0))>self.limits.max_leverage:return RiskApproval(False,'leverage limit')
        if decision.action not in ('HOLD','CLOSE') and decision.confidence<self.limits.min_confidence:return RiskApproval(False,'confidence below threshold')
        return RiskApproval(True,'approved',self.limits.max_position_pct)
