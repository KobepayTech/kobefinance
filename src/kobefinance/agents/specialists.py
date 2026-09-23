"""Finance-specialist council inspired by Anthropic financial-services workflows.
Original KobeFinance implementation; no upstream prompts are embedded here.
"""
from dataclasses import dataclass
from typing import Any,Callable
@dataclass(frozen=True)
class Evidence:
    agent:str; stance:str; confidence:float; summary:str; data:dict[str,Any]|None=None
class SpecialistCouncil:
    ROLES=('research','quant','regime','portfolio','valuation','earnings','critic')
    def __init__(self,run_agent:Callable[[str,dict],Evidence]): self.run_agent=run_agent
    def evaluate(self,state): return [self.run_agent(role,state) for role in self.ROLES]
