"""SQLite repository for fictional practice returns."""
import json
import secrets
import sqlite3
from contextlib import contextmanager
from app.services.filing import PAGES

class ReturnStore:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS practice_returns (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL,
                    completed TEXT NOT NULL DEFAULT '[]', last_step INTEGER NOT NULL DEFAULT 0,
                    updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS sections (
                    return_id TEXT NOT NULL REFERENCES practice_returns(id) ON DELETE CASCADE,
                    category TEXT NOT NULL, data TEXT NOT NULL,
                    PRIMARY KEY(return_id, category));
                CREATE TABLE IF NOT EXISTS dependents (
                    return_id TEXT NOT NULL REFERENCES practice_returns(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY(return_id, position));
                CREATE TABLE IF NOT EXISTS w2s (
                    return_id TEXT NOT NULL REFERENCES practice_returns(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY(return_id, position));
            ''')

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db: yield db
        finally: db.close()

    def create(self, owner, name):
        identifier=secrets.token_urlsafe(24)
        with self.connect() as db:
            db.execute('INSERT INTO practice_returns(id,owner,name) VALUES(?,?,?)',(identifier,owner,name))
        return identifier

    def list(self, owner):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM practice_returns WHERE owner=? ORDER BY updated DESC, rowid DESC',(owner,))]

    def get(self, identifier, owner):
        with self.connect() as db:
            row=db.execute('SELECT * FROM practice_returns WHERE id=? AND owner=?',(identifier,owner)).fetchone()
            if not row: return None
            meta=dict(row); meta['completed']=json.loads(meta['completed'])
            data={}
            for section in db.execute('SELECT data FROM sections WHERE return_id=?',(identifier,)):
                data.update(json.loads(section['data']))
            for table in ('dependents','w2s'):
                data[table]=[json.loads(r['data']) for r in db.execute(f'SELECT data FROM {table} WHERE return_id=? ORDER BY position',(identifier,))]
            return meta,data

    def save(self, identifier, owner, data, step, complete=True):
        record=self.get(identifier,owner)
        if not record: raise KeyError(identifier)
        completed=set(record[0]['completed'])
        if step != len(PAGES)-1: completed.discard(len(PAGES)-1)
        if complete: completed.add(step)
        with self.connect() as db:
            for category in {p[0] for p in PAGES}:
                keys={f[0] for stage,_,fields in PAGES if stage==category for f in fields}
                existing=db.execute('SELECT data FROM sections WHERE return_id=? AND category=?',(identifier,category)).fetchone()
                values=json.loads(existing['data']) if existing else {}
                values.update({k:data[k] for k in keys if k in data})
                db.execute('INSERT OR REPLACE INTO sections VALUES(?,?,?)',(identifier,category,json.dumps(values)))
            for table in ('dependents','w2s'):
                db.execute(f'DELETE FROM {table} WHERE return_id=?',(identifier,))
                db.executemany(f'INSERT INTO {table} VALUES(?,?,?)',[(identifier,n,json.dumps(row)) for n,row in enumerate(data.get(table,[]))])
            known={f[0] for _,_,fields in PAGES for f in fields} | {'dependents','w2s'}
            legacy={k:v for k,v in data.items() if k not in known}
            db.execute('INSERT OR REPLACE INTO sections VALUES(?,?,?)',(identifier,'legacy',json.dumps(legacy)))
            db.execute('UPDATE practice_returns SET completed=?,last_step=?,updated=CURRENT_TIMESTAMP WHERE id=? AND owner=?',(json.dumps(sorted(completed)),step,identifier,owner))

    def delete(self, identifier, owner):
        with self.connect() as db:
            db.execute('DELETE FROM practice_returns WHERE id=? AND owner=?',(identifier,owner))
