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


def test_live_mode_builds_proposal_without_calling_broker():
    from types import SimpleNamespace
    from unittest.mock import Mock

    from kobefinance.autonomy.engine import AutonomousEngine, AutonomyMode

    broker = Mock()
    memory = Mock()
    memory.recall.return_value = []
    engine = AutonomousEngine(
        state_builder=SimpleNamespace(snapshot=lambda _: {'equity': 10_000, 'price': 20}),
        memory=memory,
        planner=SimpleNamespace(plan=lambda *_: None),
        decision_model=SimpleNamespace(decide=lambda _: AutonomousDecision('LONG', .99)),
        risk_governor=RiskGovernor(),
        broker=broker,
        mode=AutonomyMode.LIVE,
    )
    event = engine.tick('TEST')
    assert event['proposal'].request.quantity == 10
    assert 'execution' not in event
    broker.execute_autonomous.assert_not_called()


def test_autonomous_execution_rejects_non_paper_broker():
    import pytest

    from kobefinance.autonomy.execution import AutonomousBrokerAdapter

    with pytest.raises(TypeError, match='paper broker'):
        AutonomousBrokerAdapter(object())
