"""Provider-neutral professional finance skill catalogue.
Conceptually incorporates workflows exposed by anthropics/financial-services
without requiring Claude or copying its prompt text.
"""
from dataclasses import dataclass
@dataclass(frozen=True)
class FinanceSkill:
    name:str; horizon:str; required_inputs:tuple[str,...]; output:str
class FinanceSkillRegistry:
    def __init__(self):
        self._skills={s.name:s for s in (
          FinanceSkill('equity_research','weeks-months',('fundamentals','prices','news'),'thesis'),
          FinanceSkill('earnings_review','days-weeks',('earnings','estimates','transcript'),'surprise/catalysts'),
          FinanceSkill('dcf','months-years',('financials','assumptions'),'intrinsic_value'),
          FinanceSkill('comps','months',('peer_multiples','financials'),'relative_value'),
          FinanceSkill('three_statement','months-years',('income','balance_sheet','cash_flow'),'financial_health'),
          FinanceSkill('portfolio_monitoring','continuous',('positions','prices','risk'),'portfolio_risk'),
          FinanceSkill('macro_fx','days-months',('rates','macro','fx'),'macro_regime'),
          FinanceSkill('fund_analysis','months',('nav','holdings','income'),'fund_quality'),
        )}
    def names(self): return tuple(self._skills)
    def get(self,name): return self._skills[name]
