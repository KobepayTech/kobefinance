from kobefinance.autonomy.engine import AutonomousDecision
from kobefinance.risk.governor import RiskGovernor,RiskLimits

def test_risk_vetoes_drawdown():
    r=RiskGovernor(RiskLimits(max_drawdown_pct=.1))
    assert not r.evaluate({'drawdown_pct':.11},AutonomousDecision('LONG',.99)).approved

def test_risk_vetoes_low_confidence_entry():
    r=RiskGovernor(RiskLimits(min_confidence=.8))
    assert not r.evaluate({},AutonomousDecision('LONG',.7)).approved

def test_close_is_not_blocked_by_low_confidence():
    r=RiskGovernor(RiskLimits(min_confidence=.99))
    assert r.evaluate({},AutonomousDecision('CLOSE',.1)).approved
