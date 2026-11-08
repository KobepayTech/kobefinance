from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from kobefinance.autonomy.live_proposal import LiveProposalBuilder
class AutonomyMode(str,Enum): RESEARCH='research'; PAPER='paper'; LIVE='live'
@dataclass(frozen=True)
class AutonomousDecision:
    action:str; confidence:float; reason:str=''
class DecisionModel(Protocol):
    def decide(self,state:dict[str,Any])->AutonomousDecision: ...
class AutonomousEngine:
    def __init__(self,*,state_builder,memory,planner,decision_model,risk_governor,broker,mode=AutonomyMode.RESEARCH):
        self.state_builder,self.memory,self.planner=state_builder,memory,planner
        self.decision_model,self.risk_governor,self.broker,self.mode=decision_model,risk_governor,broker,mode
    def tick(self,symbol):
        state=self.state_builder.snapshot(symbol); context=self.memory.recall(state); plan=self.planner.plan(state,context)
        enriched={**state,'plan':plan,'memory':context}; decision=self.decision_model.decide(enriched); approval=self.risk_governor.evaluate(enriched,decision)
        event={'symbol':symbol,'state':state,'plan':plan,'decision':decision,'risk':approval,'mode':self.mode.value}
        if self.mode == AutonomyMode.PAPER and approval.approved:
            event['execution'] = self.broker.execute_autonomous(symbol, decision, approval)
        elif self.mode == AutonomyMode.LIVE and approval.approved:
            event['proposal'] = LiveProposalBuilder().build(
                symbol, decision, approval, enriched.get('equity', 0), enriched.get('price', 0)
            )
        self.memory.record(event); return event
