from __future__ import annotations
import json,sqlite3,time
class TradeMemory:
    def __init__(self,path='kobefinance_autonomy.sqlite3'):
        self.db=sqlite3.connect(path); self.db.execute('create table if not exists events(ts real,symbol text,payload text)'); self.db.commit()
    def recall(self,state,limit=25):
        symbol=state.get('symbol',''); rows=self.db.execute('select payload from events where symbol=? order by ts desc limit ?',(symbol,limit)).fetchall(); return [json.loads(r[0]) for r in rows]
    def record(self,event):
        def default(o): return getattr(o,'__dict__',str(o))
        self.db.execute('insert into events values(?,?,?)',(time.time(),event.get('symbol',''),json.dumps(event,default=default))); self.db.commit()
