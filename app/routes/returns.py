"""Saved-return management pages."""
from flask import current_app, render_template, request, redirect, url_for, session, abort
from .session import identity, check_csrf, store

def register_routes(app):
    @app.get('/returns')
    def saved_returns():
        owner = identity()
        records = store().list(owner)
        for record in records:
            import json
            if record['name'] == 'Untitled practice return':
                record['name'] = 'Untitled return'
            record['count'] = len(json.loads(record['completed']))
        return render_template('returns.html', records=records, csrf=session['csrf'])

    @app.post('/returns/new')
    def new_return():
        check_csrf()
        identifier = store().create(identity(), request.form.get('name','').strip()[:100] or 'Untitled return')
        session['return_id'] = identifier
        return redirect(url_for('filing', step=0))

    @app.post('/returns/<identifier>/open')
    def open_return(identifier):
        check_csrf()
        record = store().get(identifier, identity())
        if not record:
            abort(404)
        session['return_id'] = identifier
        return redirect(url_for('filing', step=record[0]['last_step']))

    @app.post('/returns/<identifier>/delete')
    def delete_return(identifier):
        check_csrf()
        if not store().get(identifier, identity()):
            abort(404)
        current_app.extensions['documents'].clear(identifier, identity())
        store().delete(identifier, identity())
        if session.get('return_id') == identifier:
            session.pop('return_id', None)
        return redirect(url_for('saved_returns'))

