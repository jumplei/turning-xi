"""Offline tests; every model transport is mocked."""
import json
import os
import unittest
from unittest.mock import patch
from backend.engine import context
from backend.match_clock import DEMO_GOAL
from backend.evidence_tools import execute_calls, EvidenceWorkflowError
from backend import narrative
from backend.verification import fact_catalog,validate_claims,ClaimValidationError
from tests.test_narrative import FakeResponse


def call(name, arguments='{}', identity='call_one'):
    return dict(type='function_call', name=name, arguments=arguments, call_id=identity)


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.ctx=context(DEMO_GOAL)
        narrative.CACHE.clear(); narrative.CALLS.clear()

    def test_tools_are_snapshot_bound_and_revision_isolated(self):
        for revision in ['original','goal_removed']:
            ctx=context(DEMO_GOAL,revision=revision)
            results,trace=execute_calls([call('get_event_sequence'),call('get_personnel_state',identity='call_two')],ctx)
            for result in results:
                data=json.loads(result['output'])
                self.assertEqual(data['revision'],ctx['revision']['id'])
                self.assertEqual(data['through_second'],DEMO_GOAL)
                self.assertTrue(all(e['second']<=DEMO_GOAL for e in data.get('events',[])))
            self.assertEqual(len(trace),2)

    def test_rejects_unknown_tools_time_overrides_duplicates_and_missing_sequence(self):
        bad=[[],[call('shell')],[call('get_event_sequence','{"second":99999}')],
             [call('get_event_sequence'),call('get_event_sequence',identity='two')],
             [call('get_event_sequence'),call('get_personnel_state')],
             [call('get_personnel_state')], [call('get_event_sequence')]*4]
        for calls in bad:
            with self.subTest(calls=calls),self.assertRaises(EvidenceWorkflowError): execute_calls(calls,self.ctx)

    def test_window_facts_and_caution_history_are_prefix_bounded(self):
        from backend.engine import EVENTS
        red=next(e for e in EVENTS if e['type']=='card' and e.get('card_reason')=='second_yellow')
        before=context(red['second']-1);after=context(red['second'])
        self.assertTrue(all(e['second']<=before['second'] for e in before['discipline_events']))
        self.assertFalse(any(e['id']==red['id'] for e in before['discipline_events']))
        self.assertTrue(any(e['id']==red['id'] for e in after['discipline_events']))
        yellow=[e for e in after['discipline_events'] if e['player_id']==red['player_id'] and e['card_color']=='yellow']
        self.assertEqual(len(yellow),2)
        self.assertGreater(yellow[-1]['second']-yellow[0]['second'],300)
        catalog=fact_catalog(self.ctx)
        key='home.recent.pressures'
        self.assertEqual(catalog[key]['value'],str(self.ctx['recent_stats']['home']['pressures']))
        result=validate_claims(dict(title='Recent pressure',text='{{'+key+'}}',claims=[dict(fact_id=key,value=catalog[key]['value'])]),self.ctx)
        self.assertEqual(result['verification']['status'],'passed')
        with self.assertRaises(EvidenceWorkflowError):
            execute_calls([call('get_event_sequence')],after)

    def test_duplicate_literal_and_player_token_is_rejected(self):
        fact=next(v for k,v in fact_catalog(self.ctx).items() if k.startswith('player.'))
        result=dict(title='A sequence',text=fact['display']+' {{'+fact['fact_id']+'}} applied pressure.',claims=[dict(fact_id=fact['fact_id'],value=fact['value'])])
        with self.assertRaises(ClaimValidationError) as rejected:
            validate_claims(result,self.ctx)
        self.assertIn('repeated_player_name',rejected.exception.issues)

    @patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com','AZURE_OPENAI_API_KEY':'mock-key'})
    def test_incomplete_response_reports_output_limit_and_retains_usage(self):
        incomplete=FakeResponse({},status='incomplete')
        incomplete.data.update(incomplete_details=dict(reason='max_output_tokens'),usage=dict(input_tokens=100,output_tokens=1200,total_tokens=1300))
        with patch('backend.narrative.urlopen',return_value=incomplete):
            result=narrative.narrate(5700,recap=True,revision='goal_removed',analysis_path='fast')
        self.assertEqual(result['source'],'template')
        self.assertEqual(result['diagnostic_code'],'model_incomplete_max_output_tokens')
        self.assertEqual(result['usage']['output_tokens'],1200)
        self.assertFalse(narrative.CACHE)

    @patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com','AZURE_OPENAI_API_KEY':'mock-key'})
    def test_recap_enum_is_snapshot_bound_and_unsupported_or_missing_goal_citations_fail(self):
        ctx=context(5700,focus='away',recap=True,revision='goal_removed')
        goal_ids=[e['id'] for e in ctx['evidence'] if e['outcome']=='goal']
        candidate=dict(title='Recap',text='The match remains level.',claims=[],evidence_ids=goal_ids)
        with patch('backend.narrative.urlopen',return_value=FakeResponse(candidate)) as transport:
            result=narrative.narrate(5700,focus='away',recap=True,revision='goal_removed',analysis_path='fast')
        self.assertEqual(result['source'],'foundry')
        payload=json.loads(transport.call_args.args[0].data)
        self.assertEqual(payload['reasoning'],dict(effort='none'))
        evidence_schema=payload['text']['format']['schema']['properties']['evidence_ids']
        self.assertEqual(evidence_schema['items']['enum'],[e['id'] for e in ctx['evidence']])
        for ids,code in [(['evt_0894'],'unsupported_evidence'),([goal_ids[0]],'missing_goal_evidence')]:
            narrative.CACHE.clear()
            with patch('backend.narrative.urlopen',return_value=FakeResponse(dict(candidate,evidence_ids=ids))):
                rejected=narrative.narrate(5700,focus='away',recap=True,revision='goal_removed',analysis_path='fast')
            self.assertEqual(rejected['source'],'template')
            self.assertEqual(rejected['diagnostic_code'],code)

    @patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com','AZURE_OPENAI_API_KEY':'mock-key'})
    def test_full_time_payload_respects_approved_byte_limit_without_dropping_context(self):
        from backend.match_clock import DURATION
        ctx=context(DURATION,recap=True)
        final=FakeResponse(dict(title='Final result',text='The match is over.',claims=[],evidence_ids=[e['id'] for e in ctx['evidence'] if e['outcome']=='goal']))
        with patch.multiple(narrative,SESSION_LIMIT=24,SESSION_CALLS=0),patch('backend.narrative.urlopen',return_value=final) as transport:
            result=narrative.narrate(DURATION,recap=True,analysis_path='fast')
        self.assertEqual(result['source'],'foundry')
        request=transport.call_args.args[0]
        self.assertLessEqual(len(request.data),16000)
        payload=json.loads(request.data)
        self.assertEqual(json.loads(payload['input'])['context'],ctx)

    @patch.dict(os.environ, {'TURNING_XI_AGENTIC':'1','AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com','AZURE_OPENAI_API_KEY':'mock-key'})
    def test_fast_path_bypasses_planner_and_records_stage_timings(self):
        final=FakeResponse(dict(title='A chance',text='An observed sequence.',claims=[],evidence_ids=[self.ctx['evidence'][0]['id']]))
        with patch('backend.narrative.urlopen',return_value=final) as transport:
            result=narrative.narrate(DEMO_GOAL,analysis_path='fast')
        self.assertEqual(transport.call_count,1)
        self.assertEqual(json.loads(transport.call_args.args[0].data)['reasoning'],dict(effort='low'))
        self.assertEqual(result['workflow']['mode'],'direct')
        self.assertIn('writer_ms',result['timings'])
        self.assertIn('validation_ms',result['timings'])
        self.assertIn('context_ms',result['timings'])
        self.assertNotIn('planner_ms',result['timings'])
        # A deep request cannot reuse the fast card's cache identity.
        plan=FakeResponse({});plan.data['output']=[call('get_event_sequence')]
        with patch('backend.narrative.urlopen',side_effect=[plan,final]) as transport:
            deep=narrative.narrate(DEMO_GOAL,analysis_path='deep')
        self.assertEqual(transport.call_count,2)
        self.assertEqual(deep['workflow']['mode'],'bounded_tools')
        self.assertIn('planner_ms',deep['timings'])
        self.assertIn('tools_ms',deep['timings'])

    @patch.dict(os.environ, {'TURNING_XI_AGENTIC':'1','AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com','AZURE_OPENAI_API_KEY':'mock-key'})
    def test_model_selects_tools_then_writes_checked_card_with_no_extra_loop(self):
        plan=FakeResponse({})
        plan.data['output']=[call('get_event_sequence'),call('compare_recent_windows',identity='two')]
        plan.data['usage']={'input_tokens':10,'output_tokens':10,'total_tokens':20}
        final=FakeResponse(dict(title='A connected sequence',text='The observed sequence ends in a chance.',claims=[],evidence_ids=[self.ctx['evidence'][0]['id']]))
        final.data['usage']={'input_tokens':20,'output_tokens':30,'total_tokens':50}
        with patch.multiple(narrative,SESSION_LIMIT=24,SESSION_CALLS=0), patch('backend.narrative.urlopen',side_effect=[plan,final]) as transport:
            result=narrative.narrate(DEMO_GOAL)
        self.assertEqual(result['source'],'foundry')
        self.assertEqual(result['workflow']['mode'],'bounded_tools')
        self.assertEqual(result['usage']['total_tokens'],70)
        self.assertEqual(transport.call_count,2)
        payload=json.loads(transport.call_args_list[1].args[0].data)
        self.assertNotIn('tools',payload)
        self.assertEqual(len([v for v in payload['input'] if v.get('type')=='function_call_output']),2)
        self.assertFalse(payload['store'])

    @patch.dict(os.environ, {'TURNING_XI_AGENTIC':'1','AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com','AZURE_OPENAI_API_KEY':'mock-key'})
    def test_bad_tool_never_reaches_writer_and_budget_reserves_two_requests(self):
        plan=FakeResponse({});plan.data['output']=[call('shell')]
        with patch('backend.narrative.urlopen',return_value=plan) as transport:
            result=narrative.narrate(DEMO_GOAL)
        self.assertEqual(transport.call_count,1)
        self.assertEqual(result['source'],'template')
        self.assertEqual(result['workflow']['status'],'blocked')
        narrative.CALLS.clear()
        with patch.multiple(narrative,SESSION_LIMIT=1,SESSION_CALLS=0):
            with patch('backend.narrative.urlopen') as transport:
                result=narrative.narrate(DEMO_GOAL)
            transport.assert_not_called()
            self.assertEqual(result['fallback_reason'],'trial_limit_reached')
