from __future__ import annotations
class CalibrationTracker:
    def __init__(self): self.rows=[]
    def add(self,confidence,correct): self.rows.append((max(0.,min(1.,float(confidence))),bool(correct)))
    def brier(self): return sum((p-float(y))**2 for p,y in self.rows)/len(self.rows) if self.rows else 0.
    def buckets(self,n=10):
        out=[]
        for i in range(n):
            vals=[(p,y) for p,y in self.rows if i/n<=p<((i+1)/n if i<n-1 else 1.000001)]
            if vals: out.append({'lo':i/n,'hi':(i+1)/n,'mean_confidence':sum(p for p,_ in vals)/len(vals),'hit_rate':sum(y for _,y in vals)/len(vals),'n':len(vals)})
        return out
