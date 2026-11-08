from kobefinance.intelligence.local_qwen import LocalQwenDecisionModel
from kobefinance.intelligence.calibration import CalibrationTracker
from kobefinance.skills.finance import FinanceSkillRegistry
class Fake:
    def generate(self,*a,**k): return '{"action":"LONG","confidence":0.82,"reason":"test"}'
def test_local_qwen_is_bounded():
    d=LocalQwenDecisionModel(Fake()).decide({'symbol':'BTC-USD'})
    assert d.action=='LONG' and d.confidence==.82
def test_finance_skills_present():
    names=FinanceSkillRegistry().names(); assert 'dcf' in names and 'equity_research' in names and 'portfolio_monitoring' in names
def test_calibration():
    c=CalibrationTracker(); c.add(.8,True); c.add(.2,False); assert c.brier()<.1
