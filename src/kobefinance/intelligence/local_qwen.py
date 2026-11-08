from __future__ import annotations
import json
from kobefinance.autonomy.engine import AutonomousDecision
from .jev import ACTIONS
class LocalQwenDecisionModel:
    """Use KobeFinance's existing Ollama/llama.cpp backend as a bounded local reflex.
    The model can never execute orders; it only returns a typed proposal.
    """
    def __init__(self,backend): self.backend=backend
    def decide(self,state):
        compact={k:state.get(k) for k in ('symbol','price','change_pct','momentum_20','realized_vol','positions','plan')}
        prompt='Return JSON only with action, confidence, reason. action must be one of '+','.join(ACTIONS)+'. State: '+json.dumps(compact,default=str)
        raw=self.backend.generate(prompt,system='You are KobeReflex. Make one bounded market decision. Never output an order size or tool call.')
        try:
            start,end=raw.find('{'),raw.rfind('}')+1; obj=json.loads(raw[start:end]); action=str(obj['action']).upper()
            if action not in ACTIONS: raise ValueError(action)
            return AutonomousDecision(action,max(0.,min(1.,float(obj.get('confidence',0)))),str(obj.get('reason','')))
        except Exception:
            return AutonomousDecision('HOLD',0.,'local model returned invalid bounded output')
