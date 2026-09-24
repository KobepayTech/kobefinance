from __future__ import annotations
def technical_snapshot(candles):
    closes=[float(c.close) for c in candles]
    if not closes:return {}
    def sma(n): return sum(closes[-n:])/min(n,len(closes))
    gains=[];losses=[]
    for a,b in zip(closes[-15:-1],closes[-14:]):
        d=b-a; gains.append(max(d,0));losses.append(max(-d,0))
    ag=sum(gains)/len(gains) if gains else 0.; al=sum(losses)/len(losses) if losses else 0.
    rsi=100. if al==0 and ag>0 else (50. if al==0 else 100-(100/(1+ag/al)))
    return {'sma_5':sma(5),'sma_20':sma(20),'rsi_14':rsi,'trend':'bullish' if sma(5)>sma(20) else 'bearish'}
