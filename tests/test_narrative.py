import json
import os
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from backend.engine import context
from backend.match_clock import DEMO_GOAL, DURATION
from backend import narrative


class FakeResponse:
    def __init__(self, result, status='completed'):
        self.data = dict(status=status, output=[dict(content=[dict(type='output_text', text=json.dumps(result))])])
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, _):
        return json.dumps(self.data).encode()


class NarrativeTests(unittest.TestCase):
    def setUp(self):
        narrative.CACHE.clear()
        narrative.CALLS.clear()

    def test_user_supplied_preview_endpoint_and_v1_endpoints(self):
        preview = 'https://aica-resource.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview'
        self.assertEqual(narrative.response_url(preview), preview)
        self.assertEqual(narrative.response_url('https://example.openai.azure.com/openai/v1/'), 'https://example.openai.azure.com/openai/v1/responses')
        with self.assertRaises(ValueError):
            narrative.response_url('https://ai.azure.com/resource/deployments/x')
        with self.assertRaises(ValueError):
            narrative.response_url('http://example.com')

    @patch.dict(os.environ, {'AZURE_OPENAI_AUTH_MODE':'managed_identity', 'AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com', 'AZURE_OPENAI_API_KEY':''})
    def test_managed_identity_without_copying_api_key(self):
        self.assertTrue(narrative.configured())
        with patch('backend.narrative.managed_credential') as credential:
            credential.return_value.get_token.return_value = SimpleNamespace(token='mock-token-not-a-secret')
            headers = narrative.authentication_headers()
            self.assertNotIn('api-key', headers)
            self.assertEqual(headers['Authorization'], 'Bearer mock-token-not-a-secret')
            credential.return_value.get_token.assert_called_once_with('https://cognitiveservices.azure.com/.default')
        with patch('backend.narrative.managed_credential', side_effect=OSError):
            self.assertEqual(narrative.narrate(DEMO_GOAL)['fallback_reason'], 'authentication_failed')

    def test_missing_credentials_are_labelled_and_cached(self):
        with patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':'', 'AZURE_OPENAI_API_KEY':''}):
            result = narrative.narrate(DEMO_GOAL)
            self.assertEqual(result['source'], 'template')
            self.assertEqual(result['fallback_reason'], 'not_configured')
            self.assertTrue(narrative.narrate(DEMO_GOAL)['cached'])
            self.assertNotEqual(narrative.narrate(DEMO_GOAL, 'analyst')['text'], result['text'])

    @patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com', 'AZURE_OPENAI_API_KEY':'test-key'})
    def test_model_and_evidence_validation(self):
        ctx = context(DEMO_GOAL)
        good = dict(title='A pressing sequence',text='Pressure precedes the chance.',claims=[],evidence_ids=[ctx['evidence'][0]['id']])
        with patch('backend.narrative.urlopen', return_value=FakeResponse(good)) as opened:
            result = narrative.narrate(DEMO_GOAL)
            self.assertEqual(result['source'], 'foundry')
            self.assertEqual(result['evidence'][0]['id'], good['evidence_ids'][0])
            req = opened.call_args[0][0]
            self.assertEqual(req.full_url, 'https://example.openai.azure.com/openai/v1/responses')
            payload = json.loads(req.data)
            self.assertFalse(payload['store'])
            self.assertEqual(payload['text']['format']['type'], 'json_schema')
        narrative.CACHE.clear()
        good['evidence_ids'] = ['future_event']
        with patch('backend.narrative.urlopen', return_value=FakeResponse(good)):
            result = narrative.narrate(DEMO_GOAL)
            self.assertEqual(result['fallback_reason'], 'invalid_model_output')
            self.assertEqual(result['source'], 'template')

    @patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com', 'AZURE_OPENAI_API_KEY':'test-key'})
    def test_transient_failure_can_retry(self):
        with patch('backend.narrative.urlopen', side_effect=TimeoutError):
            self.assertEqual(narrative.narrate(DEMO_GOAL)['fallback_reason'], 'connection_failed')
        self.assertEqual(len(narrative.CACHE), 0)

    @patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com', 'AZURE_OPENAI_API_KEY':'test-key'})
    def test_full_time_insight_includes_goal_evidence(self):
        with patch('backend.narrative.azure_response', side_effect=TimeoutError) as call:
            narrative.narrate(DURATION, analysis_path='fast')
        ctx=call.call_args.args[0]
        self.assertEqual({e['id'] for e in ctx['evidence'] if e['outcome']=='goal'}, {e['event_id'] for e in ctx['goals']})
        self.assertEqual(ctx['match_status'], 'full_time')

    @patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com', 'AZURE_OPENAI_API_KEY':'test-key'})
    def test_duplicate_evidence_ids_are_deduplicated(self):
        ctx=context(DEMO_GOAL)
        event=ctx['evidence'][0]['id']
        card=dict(title='A pressing sequence',text='Pressure precedes the chance.',claims=[],evidence_ids=[event,event])
        with patch('backend.narrative.urlopen', return_value=FakeResponse(card)):
            result=narrative.narrate(DEMO_GOAL)
        self.assertEqual(result['source'], 'foundry')
        self.assertEqual([e['id'] for e in result['evidence']], [event])

    @patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com', 'AZURE_OPENAI_API_KEY':'test-key'})
    def test_rate_limit_returns_explicit_template(self):
        with patch('backend.narrative.azure_response', side_effect=TimeoutError) as call:
            for i in range(13):
                result = narrative.narrate(i*10)
            self.assertEqual(call.call_count, 12)
            self.assertEqual(result['fallback_reason'], 'rate_limited')

    @patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com', 'AZURE_OPENAI_API_KEY':'test-key'})
    def test_trial_limits_and_expiry_do_not_send_requests(self):
        with patch.multiple(narrative, SESSION_LIMIT=2, SESSION_CALLS=0, SESSION_SECONDS=1800, SESSION_STARTED=narrative.time.monotonic()):
            with patch('backend.narrative.azure_response', side_effect=TimeoutError) as call:
                narrative.narrate(10)
                narrative.narrate(20)
                self.assertEqual(narrative.narrate(30)['fallback_reason'], 'trial_limit_reached')
                self.assertEqual(call.call_count, 2)
        with patch.multiple(narrative, SESSION_LIMIT=8, SESSION_CALLS=0, SESSION_SECONDS=1, SESSION_STARTED=narrative.time.monotonic()-2):
            with patch('backend.narrative.azure_response') as call:
                self.assertEqual(narrative.narrate(40)['fallback_reason'], 'trial_expired')
                call.assert_not_called()


if __name__ == '__main__':
    unittest.main()
