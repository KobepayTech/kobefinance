from kobefinance.intelligence.technicals import technical_snapshot
from kobefinance.intelligence.factors import FactorCalibrator
from kobefinance.autonomy.live_proposal import LiveProposalBuilder
from kobefinance.autonomy.engine import AutonomousDecision
from kobefinance.risk.governor import RiskApproval
from kobefinance.services.trading.broker import Side
class C:
    def __init__(self,x):self.close=x
def test_technicals():
    s=technical_snapshot([C(x) for x in range(1,30)]); assert s['trend']=='bullish' and s['rsi_14']>50
def test_factor_calibration():
    f=FactorCalibrator();f.update({'momentum':1},1);assert f.score({'momentum':1})>0
def test_live_proposal_is_sized_but_not_submitted():
    p=LiveProposalBuilder().build('EURUSD',AutonomousDecision('LONG',.9,'x'),RiskApproval(True,'ok',.02),100000,2)
    assert p.request.side is Side.BUY and p.request.quantity==1000
