"""Browser identity and active practice-return helpers."""
import secrets
from flask import session, request, abort, current_app

def store():
    return current_app.extensions["return_store"]

def identity():
    if 'owner' not in session:
        session['owner'] = secrets.token_urlsafe(24)
    if current_app.config.get('SEED_SAMPLE_RETURNS'):
        from app.seed import ensure_sample_returns
        ensure_sample_returns(store(), current_app.extensions['documents'], session['owner'])
    if 'csrf' not in session:
        session['csrf'] = secrets.token_urlsafe(24)
    return session['owner']

def check_csrf():
    identity()
    if not secrets.compare_digest(request.form.get('csrf', ''), session['csrf']):
        abort(400)

def practice():
    owner = identity()
    record = store().get(session.get('return_id',''), owner)
    if record is None:
        session['return_id'] = store().create(owner, 'Untitled return')
        record = store().get(session['return_id'], owner)
    return record[1]

