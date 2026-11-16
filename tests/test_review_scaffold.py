"""Starter tests for the review scaffold. None of them call the Claude API."""
import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.services.review_agent.runner import ReviewOutcome
from app.services.review_agent.schema import REPORT_EXAMPLE, validate_report
from app.services.review_agent.snapshot import build_snapshot, data_hash


async def fake_runner(ctx):
    ctx.audit.append({'event': 'tool_call', 'tool': 'run_diagnostics', 'detail': 'ok'})
    return ReviewOutcome(report=REPORT_EXAMPLE, cost_usd=0.0123, turns=2)


async def failing_runner(ctx):
    raise RuntimeError('boom')


async def empty_runner(ctx):
    return None


class ReviewScaffoldTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test-key', 'REVIEW_RUNNER': fake_runner,
                               'DATABASE': str(Path(self.temp.name) / 'test.db'),
                               'DOCUMENT_DIRECTORY': str(Path(self.temp.name) / 'documents')})
        self.client = self.app.test_client()
        self.client.get('/filing/0')
        with self.client.session_transaction() as s:
            self.csrf, self.owner, self.return_id = s['csrf'], s['owner'], s['return_id']

    def run_review(self):
        return self.client.post('/review', data={'csrf': self.csrf})

    def summary(self):
        return self.client.get('/filing/13').get_data(as_text=True)

    def test_panel_is_on_the_summary_page_only(self):
        self.assertIn('id="review-panel"', self.summary())
        self.assertNotIn('id="review-panel"', self.client.get('/filing/7').get_data(as_text=True))

    def test_review_is_saved_and_shown(self):
        self.assertEqual(self.run_review().status_code, 302)
        page = self.summary()
        for expected in ('HOLD', 'W2_WAGES_MISMATCH', 'run_diagnostics', 'Cost $0.0123', '2 turns'):
            self.assertIn(expected, page)
        self.assertNotIn('changed after the last review', page)

    def test_review_goes_stale_when_the_return_changes(self):
        self.run_review()
        self.client.post('/filing/1', data={'csrf': self.csrf, 'action': 'continue', 'status': 'Single'})
        self.assertIn('changed after the last review', self.summary())

    def test_runner_error_is_saved_and_shown(self):
        self.app.config['REVIEW_RUNNER'] = failing_runner
        self.run_review()
        self.assertIn('Review failed: RuntimeError: boom', self.summary())

    def test_runner_returning_no_report_is_shown(self):
        self.app.config['REVIEW_RUNNER'] = empty_runner
        self.run_review()
        self.assertIn('returned no report', self.summary())

    def test_review_requires_csrf(self):
        self.assertEqual(self.client.post('/review', data={}).status_code, 400)

    def test_reviews_are_deleted_with_the_return(self):
        self.run_review()
        store = self.app.extensions['review_store']
        self.assertIsNotNone(store.latest(self.return_id))
        self.app.extensions['return_store'].delete(self.return_id, self.owner)
        self.assertIsNone(store.latest(self.return_id))

    def test_snapshot_hash_changes_with_the_return(self):
        args = (self.app.extensions['documents'], self.app.extensions['return_store'], self.return_id, self.owner)
        before = data_hash(build_snapshot(*args))
        self.assertEqual(before, data_hash(build_snapshot(*args)))
        meta, data = args[1].get(self.return_id, self.owner)
        data['first'] = 'Changed'
        args[1].save(self.return_id, self.owner, data, 0, complete=False)
        self.assertNotEqual(before, data_hash(build_snapshot(*args)))

    def test_report_schema_validation(self):
        self.assertEqual(validate_report(REPORT_EXAMPLE), [])
        self.assertTrue(validate_report({}))
        self.assertTrue(validate_report({**REPORT_EXAMPLE, 'verdict': 'maybe'}))
        self.assertTrue(validate_report({**REPORT_EXAMPLE, 'verdict': 'pass'}))  # pass cannot carry a blocker
        question = {'question': 'Did Avery live with you?', 'reason': 'New dependent this year.'}
        clear = {**REPORT_EXAMPLE, 'findings': [], 'client_questions': []}
        self.assertEqual(validate_report({**clear, 'verdict': 'pass'}), [])
        self.assertTrue(validate_report({**clear, 'verdict': 'pass', 'client_questions': [question]}))  # pass cannot leave questions open
        self.assertTrue(validate_report({**REPORT_EXAMPLE, 'verdict': 'warn'}))  # warn cannot carry a blocker


if __name__ == '__main__':
    unittest.main()
