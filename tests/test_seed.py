import tempfile
import unittest
from pathlib import Path

from app import create_app


class SeedTest(unittest.TestCase):
    def test_new_session_gets_three_sample_returns(self):
        with tempfile.TemporaryDirectory() as temp:
            app = create_app({'TESTING': True, 'SECRET_KEY': 'k', 'SEED_SAMPLE_RETURNS': True,
                              'DATABASE': str(Path(temp) / 't.db'), 'DOCUMENT_DIRECTORY': str(Path(temp) / 'docs')})
            client = app.test_client()
            page = client.get('/returns').get_data(as_text=True)
            for name in ('Milo Ledger 2026 (clean)', 'Milo Ledger 2026 (needs review)', 'Milo Ledger 2025 (prior year)'):
                self.assertIn(name, page)
            with client.session_transaction() as s:
                owner = s['owner']
            store, docs = app.extensions['return_store'], app.extensions['documents']
            by_name = {r['name']: r['id'] for r in store.list(owner)}
            needs = by_name['Milo Ledger 2026 (needs review)']
            self.assertEqual(len(docs.list(needs, owner)), 2)
            self.assertEqual(docs.prior(needs, owner)[0]['id'], by_name['Milo Ledger 2025 (prior year)'])
            self.assertEqual(store.get(needs, owner)[1]['w2s'][0]['wages'], '52400.00')

    def test_existing_session_without_samples_gets_them(self):
        with tempfile.TemporaryDirectory() as temp:
            app = create_app({'TESTING': True, 'SECRET_KEY': 'k', 'DATABASE': str(Path(temp) / 't.db'),
                              'DOCUMENT_DIRECTORY': str(Path(temp) / 'docs')})
            client = app.test_client()
            self.assertNotIn('Milo', client.get('/returns').get_data(as_text=True))
            app.config['SEED_SAMPLE_RETURNS'] = True
            page = client.get('/returns').get_data(as_text=True)
            self.assertEqual(page.count('Milo Ledger 2026 (clean)'), 1)
            page = client.get('/returns').get_data(as_text=True)
            self.assertEqual(page.count('Milo Ledger 2026 (clean)'), 1)

    def test_seeding_is_off_by_default(self):
        with tempfile.TemporaryDirectory() as temp:
            app = create_app({'TESTING': True, 'SECRET_KEY': 'k', 'DATABASE': str(Path(temp) / 't.db'),
                              'DOCUMENT_DIRECTORY': str(Path(temp) / 'docs')})
            self.assertNotIn('Milo', app.test_client().get('/returns').get_data(as_text=True))
