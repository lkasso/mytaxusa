"""Owned attachments and an explicit prior-year practice-return link."""
from flask import current_app, render_template, request, session, abort, redirect, url_for, send_file, jsonify
from .session import identity, practice, check_csrf, store
from app.services.diagnostics import evaluate
from app.services.extraction import extract

def service():return current_app.extensions['documents']

def register_routes(app):
    @app.route('/return-resources',methods=['GET','POST'])
    def return_resources():
        practice();identifier=session['return_id'];owner=identity();error=None
        if request.method=='POST':
            check_csrf()
            try:
                if request.form.get('action')=='link':service().link_prior(identifier,owner,request.form.get('prior_id',''))
                elif request.form.get('action')=='delete':service().delete(identifier,owner,request.form.get('document_id',''))
                else:
                    file=request.files.get('document')
                    if not file:raise ValueError('Choose a document to attach.')
                    service().upload(identifier,owner,file,request.form.get('form_type','Other'))
                return redirect(url_for('return_resources'))
            except KeyError:abort(404)
            except ValueError as exc:error=str(exc)
        prior=service().prior(identifier,owner)
        return render_template('resources.html',documents=service().list(identifier,owner),returns=[r for r in store().list(owner) if r['id']!=identifier],prior=prior[0] if prior else None,error=error,csrf=session['csrf'])

    @app.post('/documents/upload')
    def upload_document():
        practice();check_csrf()
        form_type=request.form.get('form_type','')
        steps={'W-2':4,'1099-INT':5,'1099-G':5,'1040-ES':12,'4868':12}
        try:
            if form_type not in steps:raise ValueError('Choose a supported document type.')
            file=request.files.get('document')
            if not file:raise ValueError('Choose a document to attach.')
            document=service().upload(session['return_id'],identity(),file,form_type)
            extraction=extract(service().directory/document['id'],form_type)
            if request.accept_mimetypes.best=='application/json':return jsonify(document=document,extraction=extraction),201
            return redirect(url_for('filing',step=steps[form_type]))
        except ValueError as exc:
            return jsonify(error=str(exc)),400

    @app.post('/documents/<document_id>/extract')
    def extract_document(document_id):
        practice();check_csrf()
        document=service().get(session['return_id'],identity(),document_id)
        if not document:abort(404)
        return jsonify(document=document,extraction=extract(service().directory/document['stored_name'],document['form_type']))

    @app.get('/documents/<document_id>')
    def download_document(document_id):
        practice();document=service().get(session['return_id'],identity(),document_id)
        if not document:abort(404)
        response=send_file(service().directory/document['stored_name'],as_attachment=True,download_name=document['name'],mimetype=document['media_type'])
        response.headers['X-Content-Type-Options']='nosniff'
        return response

    @app.get('/diagnostics')
    def diagnostics():
        data=practice();prior=service().prior(session['return_id'],identity())
        return jsonify(findings=[f.to_dict() for f in evaluate(data,prior[1] if prior else None)])
