from __future__ import annotations
import threading,time
class Heartbeat:
    """Simple stoppable scheduler for autonomous paper/live ticks."""
    def __init__(self,fn,interval_s=30.):
        self.fn=fn; self.interval_s=float(interval_s); self._stop=threading.Event(); self._thread=None
    def start(self):
        if self._thread and self._thread.is_alive(): return self
        def loop():
            while not self._stop.is_set():
                started=time.monotonic()
                try:self.fn()
                finally:self._stop.wait(max(0.,self.interval_s-(time.monotonic()-started)))
        self._thread=threading.Thread(target=loop,name='kobe-autonomy',daemon=True); self._thread.start(); return self
    def stop(self): self._stop.set()
