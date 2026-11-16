"""On-demand practice Form 1040 downloads for the active owned return."""
from flask import render_template, send_file
from app.services.form1040 import generate
from app.services.diagnostics import evaluate
from .session import practice

def register_routes(app):
    @app.get('/return/form-1040.pdf')
    def download_1040():
        data=practice()
        findings=evaluate(data)
        if any(f.severity=='error' for f in findings):
            return render_template('pdf_blocked.html',findings=findings),409
        response=send_file(generate(data),mimetype='application/pdf',as_attachment=True,download_name='MyTaxUSA-practice-1040.pdf')
        response.headers['Cache-Control']='no-store'
        return response
