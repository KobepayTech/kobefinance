from dataclasses import dataclass
@dataclass
class StrategyScore:
    name:str; net_return:float; max_drawdown:float; sharpe:float; observations:int
class StrategyArena:
    """Ranks only strategies that have enough observations; promotion remains deterministic."""
    def __init__(self,min_observations=100): self.min_observations=min_observations; self.scores={}
    def update(self,score): self.scores[score.name]=score
    def eligible(self): return sorted((s for s in self.scores.values() if s.observations>=self.min_observations),key=lambda s:(s.sharpe,-s.max_drawdown,s.net_return),reverse=True)
