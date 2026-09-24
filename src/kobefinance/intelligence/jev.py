from typing import Any,Callable
from kobefinance.autonomy.engine import AutonomousDecision
ACTIONS=('LONG','SHORT','HOLD','REDUCE','CLOSE')
class JevDecisionAdapter:
    def __init__(self,evaluate): self.evaluate=evaluate
    def decide(self,state):
        out=self.evaluate(state,ACTIONS); action=str(out['action']).upper()
        if action not in ACTIONS: raise ValueError('invalid bounded action')
        return AutonomousDecision(action,float(out.get('confidence',0)),str(out.get('reason','')))
class LocalBoundedDecisionAdapter:
    def __init__(self,predict): self.predict=predict
    def decide(self,state):
        probs=self.predict(state,ACTIONS); action=max(ACTIONS,key=lambda a:float(probs.get(a,0)))
        return AutonomousDecision(action,float(probs.get(action,0)),'local bounded-decision model')
