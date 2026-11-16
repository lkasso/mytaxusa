"""Manual-entry filing pages."""
import secrets
from decimal import InvalidOperation
from flask import current_app, render_template, request, redirect, url_for, session, abort
from app.services.filing import PAGES, STAGES, totals
from app.services.workflow import next_step, summary_rows
from app.validation.filing import validate_page
from app.validation.scope import UNAVAILABLE, unavailable
from app.validation.required import required_fields, RequiredFieldsError
from app.services.diagnostics import evaluate
from app.services.field_errors import field_errors
from app.services.rules import VERSION
from .review import review_view
from .session import identity, practice, store

def register_routes(app):
    @app.route('/filing/<int:step>', methods=['GET', 'POST'])
    def filing(step):
        if step >= len(PAGES):
            abort(404)
        data = practice()
        stage, title, fields = PAGES[step]
        error = None
        required_errors = {}
        if request.method == 'POST':
            if not secrets.compare_digest(request.form.get('csrf', ''), session['csrf']):
                abort(400)
            draft = dict(data)
            try:
                validate_page(step, fields, request.form, draft)
                if step == len(PAGES)-1 and request.form.get('action') == 'reviewed':
                    findings=evaluate(draft)
                    if any(f.severity=='error' for f in findings):
                        raise ValueError('Resolve the blocking findings before marking this summary reviewed.')
                    # LAB STRETCH: require a fresh AI review that is not a hold.
                    # review = review_view(step)
                    # if not review or review['status'] != 'complete' or review['stale'] or review['verdict'] == 'hold':
                    #     raise ValueError('Run the AI review and clear any hold before marking this summary reviewed.')
                data.update(draft)
                store().save(session['return_id'], identity(), data, step, complete=request.form.get('action') != 'back')
                if step == len(PAGES)-1 and request.form.get('action') == 'reviewed':
                    return redirect(url_for('saved_returns'))
                return redirect(url_for('filing', step=next_step(step, request.form.get('action'))))
            except (ValueError, InvalidOperation) as exc:
                if request.form.get('action')=='back':
                    return redirect(url_for('filing',step=next_step(step,'back')))
                error = str(exc) if isinstance(exc,ValueError) else 'Enter a valid amount.'
                data = draft
                if isinstance(exc, RequiredFieldsError):
                    required_errors = exc.errors
        prior=current_app.extensions['documents'].prior(session['return_id'],identity())
        findings=evaluate(data, prior[1] if prior else None)
        if step in (7,11):
            findings=[finding for finding in findings if finding.step<=step]
        blocked=any(f.severity=='error' for f in findings)
        inline_errors={**field_errors(data,findings,fields,request.form if error else None), **required_errors}
        editable={key for key,_,_,_ in fields}
        if step in (2,4):
            prefix='dependent_' if step==2 else 'w2_'
            editable.update(key for key in inline_errors if key.startswith(prefix))
        visible_findings=[]
        for finding in findings:
            if step in (7,11,13):
                visible_findings.append(finding)
            elif finding.step==step:
                mapped=field_errors(data,[finding],fields)
                if finding.severity!='error' or not (set(mapped) & editable):
                    visible_findings.append(finding)
        rows = summary_rows(step)
        return render_template('filing.html', unavailable=unavailable, unavailable_choices=UNAVAILABLE, return_id=session['return_id'], review=review_view(step), step=step, stage=stage, title=title, fields=fields,
            upload_types={4:['W-2'],5:['1099-INT','1099-G'],12:['1040-ES','4868']}.get(step,[]), documents=current_app.extensions['documents'].list(session['return_id'],identity()), data=data, error=error, required_fields=required_fields(step,data), field_errors=inline_errors, findings=visible_findings, blocked=blocked, rule_version=VERSION, stages=STAGES, stage_label=dict(STAGES)[stage],
            stage_steps={key:next(i for i,p in enumerate(PAGES) if p[0]==key) for key,_ in STAGES},
            completed=store().get(session['return_id'], identity())[0]['completed'], page_count=len(PAGES), totals=totals(data), summary_rows=rows, csrf=session['csrf'])

    @app.post('/filing/reset')
    def reset_return():
        if not secrets.compare_digest(request.form.get('csrf',''),session.get('csrf','invalid')):
            abort(400)
        identifier=request.form.get('return_id') or session.get('return_id')
        owner=identity()
        if not identifier or not store().get(identifier,owner):
            abort(404)
        # A stale tab must clear its displayed return, not a different active return.
        current_app.extensions['documents'].clear(identifier,owner)
        store().delete(identifier,owner)
        if session.get('return_id')==identifier:
            session.pop('return_id',None)
        return redirect(url_for('welcome'))
