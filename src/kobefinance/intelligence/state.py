from __future__ import annotations
import math
class MarketStateBuilder:
    """Build one shared world-state from KobeFinance provider + broker."""
    def __init__(self,provider,broker,range_key='1M'): self.provider,self.broker,self.range_key=provider,broker,range_key
    def snapshot(self,symbol):
        instruments=list(self.provider.instruments()); inst=next((x for x in instruments if x.symbol==symbol or x.uid==symbol),None)
        if inst is None: raise KeyError(symbol)
        q=self.provider.quote(inst.uid); candles=self.provider.history(inst.uid,self.range_key) or []
        closes=[c.close for c in candles][-64:]; returns=[closes[i]/closes[i-1]-1 for i in range(1,len(closes)) if closes[i-1]]
        vol=(sum((x-(sum(returns)/len(returns)))**2 for x in returns)/max(1,len(returns)-1))**.5 if len(returns)>1 else 0.
        momentum=(closes[-1]/closes[max(0,len(closes)-21)]-1) if len(closes)>1 else 0.
        acct=self.broker.account(); positions=[p for p in self.broker.positions() if p.symbol==inst.symbol]
        return {'symbol':inst.symbol,'uid':inst.uid,'price':q.price if q else (closes[-1] if closes else 0.),'change_pct':getattr(q,'change_pct',0.) if q else 0.,'momentum_20':momentum,'realized_vol':vol,'equity':acct.equity,'positions':[p.__dict__ for p in positions],'leverage':0.,'daily_loss_pct':0.,'drawdown_pct':0.}
