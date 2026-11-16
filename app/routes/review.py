"""Run a pre-filing review and show the latest one on the Summary page."""
import asyncio
from flask import current_app, redirect, session
from app.services.review_agent.runner import ReviewContext, run_review
from app.services.review_agent.snapshot import build_snapshot, data_hash
from .session import identity, practice, check_csrf


def review_view(step):
    """The latest saved review for the Summary page, marked stale if the return changed since."""
    if step != 13:
        return None
    review = current_app.extensions['review_store'].latest(session['return_id'])
    if review:
        snapshot = build_snapshot(current_app.extensions['documents'], current_app.extensions['return_store'],
                                  session['return_id'], identity())
        review['stale'] = review['data_hash'] != data_hash(snapshot)
    return review


def register_routes(app):
    @app.post('/review')
    def review():
        practice()
        check_csrf()
        return_id, owner = session['return_id'], identity()
        snapshot = build_snapshot(current_app.extensions['documents'], current_app.extensions['return_store'],
                                  return_id, owner)
        ctx = ReviewContext(return_id=return_id, owner=owner, snapshot=snapshot,
                            documents=current_app.extensions['documents'])
        runner = current_app.config.get('REVIEW_RUNNER', run_review)
        store, hashed = current_app.extensions['review_store'], data_hash(snapshot)
        try:
            outcome = asyncio.run(runner(ctx))
            if outcome is None:
                raise RuntimeError('The reviewer returned no report. Is lab step 1 done?')
            store.save(return_id, hashed, 'complete', report=outcome.report, trail=ctx.audit,
                       cost_usd=outcome.cost_usd, turns=outcome.turns)
        except Exception as exc:  # the page should always show what happened
            store.save(return_id, hashed, 'error', trail=ctx.audit, error=f'{type(exc).__name__}: {exc}'[:500])
        return redirect('/filing/13')
