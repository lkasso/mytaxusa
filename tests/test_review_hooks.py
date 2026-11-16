"""Tests for the step 5 hook. None of them call the Claude API."""
import asyncio, tempfile, unittest
from pathlib import Path

from app.services.review_agent.runner import ReviewContext

try:
    from app.services.review_agent.hooks import build_hooks
except ModuleNotFoundError as error:     # hooks.py does not exist until lab step 5
    if error.name != 'app.services.review_agent.hooks':
        raise
    build_hooks = None


@unittest.skipIf(build_hooks is None, 'Write app/services/review_agent/hooks.py in lab step 5 to run these.')
class ReviewHookTests(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp())
        (self.ws / 'documents').mkdir()
        self.pre = build_hooks(ReviewContext('r', 'o', {}, None))['PreToolUse'][0].hooks[0]

    def denied(self, tool, args, **extra):
        out = asyncio.run(self.pre({'tool_name': tool, 'tool_input': args, 'cwd': str(self.ws), **extra}, '1', None))
        return out.get('hookSpecificOutput', {}).get('permissionDecision') == 'deny'

    def test_bash_is_denied(self):
        self.assertTrue(self.denied('Bash', {'command': 'ls'}))

    def test_read_outside_folder_is_denied(self):
        self.assertTrue(self.denied('Read', {'file_path': '/etc/hosts'}))
        self.assertTrue(self.denied('Read', {'file_path': str(self.ws / '../x')}))

    def test_search_tools_are_denied(self):
        self.assertTrue(self.denied('Glob', {'pattern': '/etc/*'}))
        self.assertTrue(self.denied('Grep', {'pattern': '.', 'path': str(self.ws), 'output_mode': 'content'}))

    def test_return_json_is_allowed(self):
        self.assertFalse(self.denied('Read', {'file_path': str(self.ws / 'return.json')}))

    def test_web_tools_are_denied(self):
        self.assertTrue(self.denied('WebSearch', {'query': 'x'}))
        self.assertTrue(self.denied('WebFetch', {'url': 'https://example.com'}))

    def test_structured_output_is_allowed(self):
        self.assertFalse(self.denied('StructuredOutput', {}))


if __name__ == '__main__':
    unittest.main()
