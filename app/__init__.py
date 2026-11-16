"""Application factory and shared configuration."""
from pathlib import Path
import secrets
from flask import Flask
from app.repositories.returns import ReturnStore
from app.repositories.reviews import ReviewStore
from app.services.documents import DocumentService
from app.routes import pages, returns, filing, documents, pdf, review

def create_app(config=None):
    app = Flask(__name__, instance_path=str(Path(__file__).resolve().parent.parent / 'instance'))
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    key_file = Path(app.instance_path) / 'session.key'
    try:
        with key_file.open('xb') as file:
            file.write(secrets.token_bytes(32))
        key_file.chmod(0o600)
    except FileExistsError:
        pass
    app.secret_key = key_file.read_bytes()
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', MAX_CONTENT_LENGTH=6 * 1024 * 1024)
    app.config['DATABASE'] = str(Path(app.instance_path) / 'practice.sqlite3')
    if config:
        app.config.update(config)
    app.extensions['return_store'] = ReturnStore(app.config['DATABASE'])

    app.extensions['documents'] = DocumentService(app.extensions['return_store'], app.config.get('DOCUMENT_DIRECTORY', str(Path(app.instance_path) / 'documents')))

    app.extensions['review_store'] = ReviewStore(app.extensions['return_store'])

    @app.after_request
    def local_content_only(response):
        response.headers['Content-Security-Policy'] = (
            "default-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; form-action 'self'; frame-src 'none'"
        )
        if response.mimetype=='text/html':
            response.headers['Cache-Control']='no-store'
        return response

    for routes in (pages, returns, filing, documents, pdf, review):
        routes.register_routes(app)
    return app
