class FactorCalibrator:
    """Leakage-safe online factor weighting: update only after an outcome is known."""
    def __init__(self,alpha=.05): self.alpha=alpha; self.weights={}
    def update(self,factors,outcome):
        for name,value in factors.items():
            old=self.weights.get(name,0.); self.weights[name]=(1-self.alpha)*old+self.alpha*float(value)*float(outcome)
    def score(self,factors): return sum(float(v)*self.weights.get(k,0.) for k,v in factors.items())
