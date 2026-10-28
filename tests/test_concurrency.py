import json
import os
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from backend import narrative
from backend.engine import template


def answer(ctx,mode,language,recap,path):
    return dict(template(ctx,mode,language,recap),verification=dict(status='passed'),workflow=dict(mode='direct',steps=[]))

@patch.dict(os.environ,{'AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com','AZURE_OPENAI_API_KEY':'mock'})
class ConcurrencyTests(unittest.TestCase):
    def setUp(self):
        narrative.CACHE.clear();narrative.CALLS.clear();narrative.INFLIGHT.clear()

    def test_independent_requests_enter_transport_without_global_serialization(self):
        barrier=threading.Barrier(2)
        def transport(*args):
            barrier.wait(timeout=2)
            return answer(*args)
        with patch.multiple(narrative,SESSION_LIMIT=2,SESSION_CALLS=0,SESSION_STATE_FILE=''),patch('backend.narrative.azure_response',side_effect=transport):
            with ThreadPoolExecutor(max_workers=2) as pool:
                a=pool.submit(narrative.narrate,600,analysis_path='fast')
                b=pool.submit(narrative.narrate,601,analysis_path='fast')
                self.assertEqual(a.result(4)['source'],'foundry')
                self.assertEqual(b.result(4)['source'],'foundry')
            self.assertEqual(narrative.SESSION_CALLS,2)

    def test_same_request_is_coalesced_without_double_reserving_budget(self):
        entered=threading.Event();release=threading.Event()
        def transport(*args):
            entered.set();release.wait(2)
            return answer(*args)
        with patch.multiple(narrative,SESSION_LIMIT=1,SESSION_CALLS=0,SESSION_STATE_FILE=''),patch('backend.narrative.azure_response',side_effect=transport) as model:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first=pool.submit(narrative.narrate,600,analysis_path='fast')
                self.assertTrue(entered.wait(1))
                second=pool.submit(narrative.narrate,600,analysis_path='fast')
                release.set()
                a,b=first.result(4),second.result(4)
            self.assertEqual(a['artifact_id'],b['artifact_id'])
            self.assertEqual(model.call_count,1)
            self.assertEqual(narrative.SESSION_CALLS,1)
            self.assertFalse(narrative.INFLIGHT)

    def test_budget_reservation_is_atomic_and_persisted_before_transport(self):
        entered=threading.Event();release=threading.Event()
        with tempfile.TemporaryDirectory() as directory:
            ledger=Path(directory)/'budget.json'
            def transport(*args):
                self.assertEqual(json.loads(ledger.read_text())['calls_used'],1)
                entered.set();release.wait(2)
                return answer(*args)
            with patch.multiple(narrative,SESSION_LIMIT=1,SESSION_CALLS=0,SESSION_STATE_FILE=str(ledger)),patch('backend.narrative.azure_response',side_effect=transport) as model:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    first=pool.submit(narrative.narrate,600,analysis_path='fast')
                    self.assertTrue(entered.wait(1))
                    second=pool.submit(narrative.narrate,601,analysis_path='fast')
                    denied=second.result(1)
                    release.set();first.result(3)
                self.assertEqual(denied['fallback_reason'],'trial_limit_reached')
                self.assertEqual(model.call_count,1)
                self.assertEqual(ledger.stat().st_mode&0o777,0o600)
