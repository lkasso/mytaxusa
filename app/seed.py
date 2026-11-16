"""Lab fixture: three ready-made returns for a new browser session.

Only runs when SEED_SAMPLE_RETURNS is on (run.py turns it on). Not part of the product.
It loads what sample-documents/ describes, so nobody enters returns or uploads PDFs by hand.
"""
import json
from io import BytesIO
from pathlib import Path

SAMPLES = Path(__file__).resolve().parent.parent / 'sample-documents'
CASES = (('01-milo-clean', 'Milo Ledger 2026 (clean)'), ('02-milo-needs-review', 'Milo Ledger 2026 (needs review)'))
FORM_TYPES = {'w2': 'W-2', '1099-int': '1099-INT'}


class _Upload:
    def __init__(self, path):
        self.filename, self.stream = path.name, BytesIO(path.read_bytes())


def ensure_sample_returns(store, documents, owner):
    """Seed the sample returns for an owner that has none of them yet.

    Keyed on the owner's saved returns, not on the browser cookie, so a browser
    that already has a session still gets the returns on its next request.
    """
    names = {'Milo Ledger 2025 (prior year)', *(name for _, name in CASES)}
    if not names & {record['name'] for record in store.list(owner)}:
        seed_sample_returns(store, documents, owner)


def seed_sample_returns(store, documents, owner):
    prior = store.create(owner, 'Milo Ledger 2025 (prior year)')
    store.save(prior, owner, json.loads((SAMPLES / '00-prior-year-2025/prior-year-entries.json').read_text()), 13, complete=False)
    documents.upload(prior, owner, _Upload(SAMPLES / '00-prior-year-2025/prior-year-w2-2025.pdf'), 'W-2')
    for folder, name in CASES:
        identifier = store.create(owner, name)
        store.save(identifier, owner, json.loads((SAMPLES / folder / 'entries.json').read_text()), 13, complete=False)
        for pdf in sorted((SAMPLES / folder).glob('*.pdf')):
            form_type = next(t for key, t in FORM_TYPES.items() if key in pdf.name.lower())
            documents.upload(identifier, owner, _Upload(pdf), form_type)
        documents.link_prior(identifier, owner, prior)
