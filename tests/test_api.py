"""Real HTTP tests in an isolated child process; no model requests or Azure credit."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.match_clock import DURATION, DEMO_GOAL, HALF_TIME_START, SECOND_HALF_START


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        cls.base = 'http://127.0.0.1:%s' % port
        env = dict(os.environ, AZURE_OPENAI_ENDPOINT='', AZURE_OPENAI_API_KEY='', MATCHMIND_ACCESS_TOKEN='isolated-test-token')
        cls.server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', str(port)],
                                      cwd=Path(__file__).resolve().parent.parent, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                with urlopen(cls.base + '/api/health', timeout=.2):
                    return
            except OSError:
                time.sleep(.1)
        cls.server.terminate()
        raise RuntimeError('Test API did not start')

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.wait(timeout=5)

    def get(self, path):
        with urlopen(self.base + path, timeout=5) as response:
            return json.load(response)

    def post(self, payload, token=''):
        req = Request(self.base + '/api/insight', data=json.dumps(payload).encode(), method='POST',
                      headers={'Content-Type':'application/json', 'X-MatchMind-Token':token})
        with urlopen(req, timeout=5) as response:
            return json.load(response)

    def test_health_and_static_page(self):
        self.assertFalse(self.get('/api/health')['model_configured'])
        with urlopen(self.base + '/') as response:
            self.assertIn(b'<html lang="en">', response.read())

    def test_bounds_and_preferences_are_validated(self):
        for path in ['/api/state?second=-1', '/api/state?second=%s' % (DURATION+1)]:
            with self.assertRaises(HTTPError) as exc:
                self.get(path)
            self.assertEqual(exc.exception.code, 422)
        with self.assertRaises(HTTPError) as exc:
            self.post(dict(second=DEMO_GOAL, language='unsupported'))
        self.assertEqual(exc.exception.code, 422)

    def test_model_endpoint_requires_demo_token(self):
        with self.assertRaises(HTTPError) as exc:
            self.post(dict(second=DEMO_GOAL))
        self.assertEqual(exc.exception.code, 401)
        result = self.post(dict(second=DEMO_GOAL, mode='analyst'), 'isolated-test-token')
        self.assertEqual(result['source'], 'template')
        self.assertEqual(result['audience'], 'analyst')
        self.assertTrue(all(e['second'] <= DEMO_GOAL for e in result['evidence']))

    def test_event_export_hides_the_future(self):
        export = self.get('/api/events/export?second=600')
        self.assertGreater(len(export['events']), 1)
        self.assertEqual(len(export['events']), self.get('/api/state?second=600')['event_count'])
        self.assertTrue(all(e['second'] <= 600 for e in export['events']))

    def test_rule_bookmarks_rosters_and_offline_explanations(self):
        meta=self.get('/api/match')
        self.assertEqual(meta['dataset_version'],'3.0')
        for key in ['offside','yellow_card','red_card','second_yellow','substitution']:
            moment=next(m for m in meta['key_moments'] if m['key']==key)
            snapshot=self.get('/api/state?second=%s' % moment['second'])
            self.assertIn('lineups',snapshot)
            insight=self.post(dict(second=moment['second']),'isolated-test-token')
            self.assertEqual(insight['source'],'template')
            self.assertTrue(all(e['second']<=moment['second'] for e in insight['evidence']))
        self.assertFalse(self.get('/api/health')['model_configured'])
        self.assertEqual(self.get('/openapi.json')['info']['title'],'Turning XI')

    def test_phase_insight_cannot_use_future_or_withdrawn_phase(self):
        snapshot=self.get('/api/state?second=%s' % DEMO_GOAL)
        phase=next(p for p in snapshot['phases'] if p['end']==DEMO_GOAL)
        result=self.post(dict(second=DEMO_GOAL,phase_id=phase['id']),'isolated-test-token')
        self.assertEqual([e['id'] for e in result['evidence']],phase['event_ids'])
        self.assertEqual(result['phase_id'],phase['id'])
        for payload in [dict(second=DEMO_GOAL-1,phase_id=phase['id']),dict(second=DEMO_GOAL,phase_id=phase['id'],revision='goal_removed')]:
            with self.assertRaises(HTTPError) as exc: self.post(payload,'isolated-test-token')
            self.assertEqual(exc.exception.code,422)

    def test_correction_isolated_and_patch_withdraws_served_card(self):
        old=self.post(dict(second=DURATION,recap=True),'isolated-test-token')
        payload=dict(second=DURATION,artifacts=[dict(id='recap_'+old['artifact_id'],kind='recap',second=DURATION,revision_id='r1')])
        req=Request(self.base+'/api/corrections/preview',data=json.dumps(payload).encode(),method='POST',headers={'Content-Type':'application/json'})
        with urlopen(req) as response: audit=json.load(response)
        self.assertIn('recap_'+old['artifact_id'],[o['artifact_id'] for o in audit['operations']])
        original=self.get('/api/state?second=%s' % DURATION)
        revised=self.get('/api/state?second=%s&revision=goal_removed' % DURATION)
        self.assertEqual(original['stats']['home']['goals']-1,revised['stats']['home']['goals'])
        self.assertEqual(self.get('/api/state?second=%s' % DURATION)['revision']['id'],'r1')
        new=self.post(dict(second=DURATION,recap=True,revision='goal_removed'),'isolated-test-token')
        self.assertIn('draw',new['text'])
        self.assertNotEqual(old['artifact_id'],new['artifact_id'])

    def test_offline_verification_demo_and_invalid_revision(self):
        req=Request(self.base+'/api/verification/demo',data=json.dumps(dict(second=DEMO_GOAL)).encode(),method='POST',headers={'Content-Type':'application/json'})
        with urlopen(req) as response: result=json.load(response)
        self.assertEqual(result['status'],'blocked')
        self.assertFalse(result['model_called'])
        with self.assertRaises(HTTPError) as exc: self.get('/api/state?second=600&revision=unknown')
        self.assertEqual(exc.exception.code,422)
        self.assertEqual(self.get('/api/health')['model_session']['calls_used'],0)

    def test_schedule_drives_bounds_and_period_state(self):
        meta=self.get('/api/match')
        self.assertEqual(meta['duration'],DURATION)
        self.assertEqual(meta['schedule']['half_time_break'],900)
        self.assertEqual(self.get('/api/state?second=%s' % HALF_TIME_START)['match_status'],'half_time')
        self.assertEqual(self.get('/api/state?second=%s' % SECOND_HALF_START)['display_clock'],'45:00')
        self.assertEqual(self.get('/api/state?second=%s' % DURATION)['match_status'],'full_time')
        self.assertEqual(next(m for m in meta['key_moments'] if m['key']=='goal')['second'],DEMO_GOAL)


if __name__ == '__main__':
    unittest.main()
