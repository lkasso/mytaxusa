"""Saved AI reviews. One row per run; the newest row is the one the page shows."""
import json
import secrets


class ReviewStore:
    def __init__(self, repository):
        self.repository = repository
        with repository.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    return_id TEXT NOT NULL REFERENCES practice_returns(id) ON DELETE CASCADE,
                    data_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verdict TEXT, report TEXT, trail TEXT, cost_usd REAL, turns INTEGER, error TEXT,
                    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);''')

    def save(self, return_id, data_hash, status, report=None, trail=None, cost_usd=None, turns=None, error=None):
        verdict = report.get('verdict') if isinstance(report, dict) else None
        with self.repository.connect() as db:
            db.execute('''INSERT INTO reviews(id,return_id,data_hash,status,verdict,report,trail,cost_usd,turns,error)
                          VALUES(?,?,?,?,?,?,?,?,?,?)''',
                       (secrets.token_urlsafe(16), return_id, data_hash, status, verdict,
                        json.dumps(report), json.dumps(trail or []), cost_usd, turns, error))

    def latest(self, return_id):
        with self.repository.connect() as db:
            row = db.execute('SELECT * FROM reviews WHERE return_id=? ORDER BY created DESC, rowid DESC LIMIT 1',
                             (return_id,)).fetchone()
        if row is None:
            return None
        review = dict(row)
        review['report'] = json.loads(review['report']) if review['report'] else None
        review['trail'] = json.loads(review['trail'])
        return review
