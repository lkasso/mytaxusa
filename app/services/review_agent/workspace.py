"""The folder the review agent works in. Finished starter code, not part of the lab.

Each review gets a fresh temporary folder: a copy of `workspace-template/` (the
reviewer's conventions and skills) plus this return's data. The agent works
inside it with read-only tools, and the folder is deleted when the review ends.

    return.json       this year's return
    prior.json        last year's return, or null if none is linked
    diagnostics.json  the app's own deterministic findings
    manifest.json     the list of attached documents (agents have no way to list folders)
    documents/        the text of each attached PDF, one .txt file per document

The agent reads text, not the PDFs. The built-in Read tool returns a large PDF as
encoded content that can overflow the SDK's message buffer and your token budget.
"""
import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pdfplumber

from app.services.diagnostics import evaluate

TEMPLATE = Path(__file__).parent / 'workspace-template'


@contextmanager
def review_workspace(ctx):
    with tempfile.TemporaryDirectory(prefix='review-') as tmp:
        workspace = Path(tmp)
        shutil.copytree(TEMPLATE, workspace, dirs_exist_ok=True)
        data, prior = ctx.snapshot['data'], ctx.snapshot['prior']
        findings = [{'code': f.code, 'severity': f.severity, 'field': f.field, 'message': f.message}
                    for f in evaluate(data, prior)]
        for name, payload in (('return.json', data), ('prior.json', prior), ('diagnostics.json', findings)):
            (workspace / name).write_text(json.dumps(payload, indent=2))
        (workspace / 'documents').mkdir()
        manifest = []
        for item in ctx.snapshot['documents']:
            document = ctx.documents.get(ctx.return_id, ctx.owner, item['id'])
            with pdfplumber.open(ctx.documents.directory / document['stored_name']) as pdf:
                text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
            name = Path(item['name']).stem + '.txt'
            (workspace / 'documents' / name).write_text(text[:20000])
            manifest.append({'file': f'documents/{name}', 'uploaded_as': item['name']})
        (workspace / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        yield workspace
