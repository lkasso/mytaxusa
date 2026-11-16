"""Private local attachments; no OCR, extraction, or form autofill."""
from pathlib import Path
import secrets
from .extraction import validate_pdf
from werkzeug.utils import secure_filename

class DocumentService:
    TYPES={'W-2','1099-INT','1099-G','1040-ES','4868','Other'}
    LIMIT=5*1024*1024
    def __init__(self, repository, directory):
        self.repository=repository
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        with repository.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, return_id TEXT NOT NULL REFERENCES practice_returns(id) ON DELETE CASCADE,
                name TEXT NOT NULL, stored_name TEXT NOT NULL, size INTEGER NOT NULL, media_type TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS prior_links (
                return_id TEXT PRIMARY KEY REFERENCES practice_returns(id) ON DELETE CASCADE,
                prior_id TEXT NOT NULL REFERENCES practice_returns(id) ON DELETE CASCADE);''')
            columns={r['name'] for r in db.execute('PRAGMA table_info(documents)')}
            if 'form_type' not in columns:
                db.execute("ALTER TABLE documents ADD COLUMN form_type TEXT NOT NULL DEFAULT 'Other'")
    def authorize(self, identifier, owner):
        if not self.repository.get(identifier,owner):raise KeyError(identifier)
    def list(self, identifier, owner):
        self.authorize(identifier,owner)
        with self.repository.connect() as db:return [dict(r) for r in db.execute('SELECT * FROM documents WHERE return_id=?',(identifier,))]
    def upload(self, identifier, owner, file, form_type='Other'):
        if form_type not in self.TYPES:raise ValueError('Choose a supported document type.')
        self.authorize(identifier,owner)
        name=secure_filename(file.filename or '')
        content=file.stream.read(self.LIMIT+1)
        if not name or not content or len(content)>self.LIMIT:raise ValueError('Choose a nonempty PDF file up to 5 MB.')
        ext=Path(name).suffix.lower()
        if ext!='.pdf' or not content.startswith(b'%PDF-'):
            raise ValueError('File contents must match a PDF extension. Only PDFs are supported.')
        import io
        validate_pdf(io.BytesIO(content))
        token=secrets.token_hex(24);path=self.directory/token
        path.write_bytes(content)
        try:
            with self.repository.connect() as db:db.execute('INSERT INTO documents(id,return_id,name,stored_name,size,media_type,form_type) VALUES(?,?,?,?,?,?,?)',(token,identifier,name,token,len(content),'application/pdf',form_type))
        except Exception:
            path.unlink(missing_ok=True);raise
        return {'id':token,'name':name,'form_type':form_type}
    def get(self, identifier, owner, document_id):
        return next((d for d in self.list(identifier,owner) if d['id']==document_id),None)
    def delete(self, identifier, owner, document_id):
        document=self.get(identifier,owner,document_id)
        if not document:raise KeyError(document_id)
        # Retain the record if unlinking fails, allowing a later cleanup retry.
        (self.directory/document['stored_name']).unlink(missing_ok=True)
        with self.repository.connect() as db:db.execute('DELETE FROM documents WHERE id=?',(document_id,))
    def clear(self, identifier, owner):
        for d in self.list(identifier,owner):self.delete(identifier,owner,d['id'])
    def link_prior(self, identifier, owner, prior_id):
        self.authorize(identifier,owner)
        if prior_id:
            self.authorize(prior_id,owner)
            if prior_id==identifier:raise ValueError('Choose a different return.')
        with self.repository.connect() as db:
            db.execute('DELETE FROM prior_links WHERE return_id=?',(identifier,))
            if prior_id:db.execute('INSERT INTO prior_links VALUES(?,?)',(identifier,prior_id))
    def prior(self, identifier, owner):
        self.authorize(identifier,owner)
        with self.repository.connect() as db:row=db.execute('SELECT prior_id FROM prior_links WHERE return_id=?',(identifier,)).fetchone()
        return self.repository.get(row['prior_id'],owner) if row else None
