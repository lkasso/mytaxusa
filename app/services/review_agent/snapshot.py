"""What the reviewer sees: one frozen view of a return, plus a hash to detect changes."""
import hashlib
import json


def build_snapshot(documents, return_store, return_id, owner):
    meta, data = return_store.get(return_id, owner)
    prior = documents.prior(return_id, owner)
    attached = [dict(id=d['id'], name=d['name'], form_type=d['form_type'], size=d['size'])
                for d in documents.list(return_id, owner)]
    return dict(return_id=return_id, name=meta['name'], data=data,
                prior=prior[1] if prior else None, documents=attached)


def data_hash(snapshot):
    """Changes whenever the return, the linked prior year, or the attachments change."""
    material = {key: snapshot[key] for key in ('data', 'prior', 'documents')}
    return hashlib.sha256(json.dumps(material, sort_keys=True, default=str).encode()).hexdigest()
