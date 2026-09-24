"""PanWatch-inspired multi-agent debate, implemented natively for KobeFinance."""
from dataclasses import dataclass
@dataclass(frozen=True)
class DebateResult:
    bull:object; bear:object; risk:object; manager:object
class DebateCouncil:
    def __init__(self,run_agent): self.run_agent=run_agent
    def evaluate(self,state):
        bull=self.run_agent('bull',state); bear=self.run_agent('bear',state)
        debated={**state,'bull':getattr(bull,'__dict__',bull),'bear':getattr(bear,'__dict__',bear)}
        risk=self.run_agent('risk',debated)
        manager=self.run_agent('portfolio_manager',{**debated,'risk_review':getattr(risk,'__dict__',risk)})
        return DebateResult(bull,bear,risk,manager)
