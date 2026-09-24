from __future__ import annotations
class KobePlanner:
    """Slow System-2 planner. Backend can be local Qwen/Ollama or cloud."""
    def __init__(self,council=None,llm=None): self.council,self.llm=council,llm
    def plan(self,state,memory):
        evidence=self.council.evaluate(state) if self.council else []
        compact={'symbol':state.get('symbol'),'regime':state.get('regime'),'evidence':[getattr(x,'__dict__',x) for x in evidence],'recent_memory':memory[-5:] if memory else []}
        if self.llm:
            return {'evidence':compact['evidence'],'thesis':self.llm(compact)}
        return {'evidence':compact['evidence'],'thesis':'deterministic MVP: defer direction to bounded decision layer'}
