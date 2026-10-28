import copy
import os
import unittest
from unittest.mock import patch

from backend.engine import EVENTS, state, context
from backend.phases import detect_phases, phase_context
from backend.revisions import view_events
from backend.match_clock import DEMO_GOAL, DURATION, HALF_TIME_START
from backend.verification import fact_catalog, validate_claims, ClaimValidationError
from backend.corrections import correction_preview, verification_demo
from backend import narrative
from tests.test_narrative import FakeResponse


class PhaseTests(unittest.TestCase):
    def test_curated_chain_is_computed_and_cannot_appear_early(self):
        target=next(p for p in detect_phases(DEMO_GOAL) if p['end']==DEMO_GOAL)
        self.assertEqual(target['kind'],'recovery_to_shot')
        self.assertEqual([e['type'] for e in target['events']],['pressure','pressure','pass','pass','pass','shot'])
        self.assertEqual(target['metrics'],dict(goals=1,shots=1,complete=2,pressures=2))
        self.assertFalse(any(p['id']==target['id'] for p in detect_phases(DEMO_GOAL-1)))
        with self.assertRaises(ValueError): phase_context(DEMO_GOAL-1,target['id'])

    def test_phase_story_uses_phase_end_not_later_score_and_correction_retains_early_artifacts(self):
        at_goal=next(p for p in detect_phases(DEMO_GOAL) if p['end']==DEMO_GOAL)
        later=next(p for p in detect_phases(DURATION) if p['id']==at_goal['id'])
        self.assertEqual(at_goal['story'],later['story'])
        self.assertEqual(at_goal['story']['before_score'],dict(home=0,away=1))
        self.assertEqual(at_goal['story']['after_score'],dict(home=1,away=1))
        self.assertEqual(at_goal['story']['through_second'],DEMO_GOAL)
        early=dict(id='early',kind='insight',second=30,revision_id='r1')
        late=dict(id='late',kind='overlay',second=DEMO_GOAL,revision_id='r1')
        audit=correction_preview(DEMO_GOAL,[early,late])
        self.assertEqual(audit['retained_artifacts'],[early])
        self.assertTrue(any(o['artifact_id']=='late' and o['operation']=='withdraw' for o in audit['operations']))

    def test_all_phase_steps_are_prefix_and_period_bounded(self):
        for second in [0,600,HALF_TIME_START,DEMO_GOAL,DURATION]:
            for p in detect_phases(second):
                self.assertLessEqual(p['end'],second)
                self.assertLessEqual(len(p['events']),8)
                self.assertEqual(len(set(e['period'] for e in p['events'])),1)
                self.assertEqual(p['event_ids'],[e['id'] for e in p['events']])
                self.assertTrue(all(p['start']<=e['second']<=p['end'] for e in p['events']))

    def test_insight_uses_the_selected_phase_not_the_latest_event(self):
        phase=next(p for p in detect_phases(DEMO_GOAL) if p['end']==DEMO_GOAL)
        ctx=phase_context(DURATION,phase['id'])
        self.assertEqual(ctx['evidence'],phase['events'])
        self.assertEqual(ctx['phase']['id'],phase['id'])
        self.assertEqual(ctx['stats'],state(DURATION)['stats'])


class RevisionTests(unittest.TestCase):
    def test_revision_is_pure_prefix_local_and_reversible(self):
        original=copy.deepcopy(EVENTS)
        self.assertEqual(state(DEMO_GOAL-1),state(DEMO_GOAL-1,'goal_removed') | {'revision':state(DEMO_GOAL-1)['revision']})
        for second in [DEMO_GOAL,DURATION]:
            a,b=state(second),state(second,'goal_removed')
            for metric in ['goals','shots','on_target']:
                self.assertEqual(a['stats']['home'][metric]-1,b['stats']['home'][metric])
            self.assertEqual(a['stats']['away'],b['stats']['away'])
            self.assertEqual(a['lineups'],b['lineups'])
        self.assertEqual(EVENTS,original)
        self.assertEqual(state(DURATION)['revision']['id'],'r1')
        self.assertTrue(all(e['second']<=DEMO_GOAL for e in view_events(EVENTS,DEMO_GOAL,'goal_removed')))

    def test_withdrawal_list_matches_actual_snapshot_dependencies(self):
        artifacts=[dict(id='old_story',kind='insight',second=DEMO_GOAL,revision_id='r1'),
                   dict(id='old_recap',kind='recap',second=DURATION,revision_id='r1'),
                   dict(id='old_overlay',kind='overlay',second=DURATION,revision_id='r1'),
                   dict(id='before_goal',kind='insight',second=600,revision_id='r1'),
                   dict(id='new_story',kind='insight',second=DURATION,revision_id='r2')]
        audit=correction_preview(DURATION,artifacts)
        withdrawn={o['artifact_id'] for o in audit['operations'] if o['operation']=='withdraw'}
        self.assertTrue({'old_story','old_recap','old_overlay'}<=withdrawn)
        self.assertNotIn('before_goal',withdrawn);self.assertNotIn('new_story',withdrawn)
        old_phase=next(p for p in detect_phases(DEMO_GOAL) if p['end']==DEMO_GOAL)
        self.assertIn(old_phase['id'],withdrawn)
        self.assertFalse(any(p['id']==old_phase['id'] for p in detect_phases(DURATION,'goal_removed')))
        self.assertEqual(audit['replacement']['revision']['id'],'r2')
        with self.assertRaises(ValueError): correction_preview(DEMO_GOAL-1)

    @patch.dict(os.environ,{'AZURE_OPENAI_ENDPOINT':'','AZURE_OPENAI_API_KEY':''})
    def test_revised_cache_recap_and_evidence_do_not_reuse_old_goal(self):
        narrative.CACHE.clear()
        before=narrative.narrate(DURATION,recap=True)
        after=narrative.narrate(DURATION,recap=True,revision='goal_removed')
        self.assertNotEqual(before['artifact_id'],after['artifact_id'])
        self.assertIn('2–1',before['text']);self.assertIn('1–1',after['text'])
        self.assertIn('draw',after['text'])
        invalid=next(e['id'] for e in EVENTS if e['second']==DEMO_GOAL)
        self.assertFalse(any(e['id']==invalid and e['outcome']=='goal' for e in after['evidence']))
        self.assertTrue(narrative.narrate(DURATION,recap=True)['cached'])


class VerificationTests(unittest.TestCase):
    def setUp(self):
        narrative.CACHE.clear();narrative.CALLS.clear()
        self.ctx=context(DEMO_GOAL)

    def card(self,claims=None,text='A cautious interpretation.'):
        return dict(title='Match read',text=text,claims=claims or [],evidence_ids=[self.ctx['evidence'][0]['id']])

    def test_valid_typed_facts_and_player_references_render_from_code(self):
        catalog=fact_catalog(self.ctx)
        claims=[dict(fact_id=k,value=catalog[k]['value']) for k in ['match.score','home.shots','home.on_pitch']]
        result=validate_claims(self.card(claims,'{{match.score}}.\n{{home.shots}}.\n{{home.on_pitch}}.'),self.ctx)
        self.assertEqual(result['verification']['status'],'passed')
        self.assertNotIn('{{',result['text'])
        self.assertIn(catalog['home.shots']['display'],result['text'])

    def test_embedded_score_uses_checked_value_and_standalone_score_keeps_label(self):
        fact=fact_catalog(self.ctx)['match.score']
        claims=[dict(fact_id='match.score',value=fact['value'])]
        prose=validate_claims(self.card(claims,'The match is level at {{match.score}}.'),self.ctx)
        self.assertEqual(prose['text'],'The match is level at 1–1.')
        standalone=validate_claims(self.card(claims,'The match is level.\n{{match.score}}'),self.ctx)
        self.assertIn(fact['display'],standalone['text'])
        self.assertEqual(prose['facts'][0],fact)
        shots=fact_catalog(self.ctx)['home.shots']
        natural=validate_claims(self.card([dict(fact_id=shots['fact_id'],value=shots['value'])],'Home have {{home.shots}} shots.'),self.ctx)
        self.assertEqual(natural['text'],'Home have 13 shots.')

    def test_qualitative_prose_keeps_score_in_code_owned_facts_for_each_revision(self):
        for revision,expected in [('original','1–1'),('goal_removed','0–1')]:
            ctx=context(DEMO_GOAL,revision=revision)
            result=validate_claims(self.card(text='An observed attacking sequence.'),ctx)
            self.assertEqual(result['text'],'An observed attacking sequence.')
            self.assertEqual(next(f['value'] for f in result['facts'] if f['fact_id']=='match.score'),expected)

    def test_wrong_score_shots_player_and_undeclared_numbers_are_blocked(self):
        for claims,text in [([dict(fact_id='match.score',value='9–9')],'No numbers.'),
                            ([dict(fact_id='home.shots',value='999')],'No numbers.'),
                            ([dict(fact_id='home.on_pitch',value='12')],'No numbers.'),
                            ([dict(fact_id='player.H99',value='H99')],'No numbers.'),
                            ([], 'Home have 99 shots.'),([], 'Z. Fabricated scored.'),
                            ([], '{{home.shots}}')]:
            with self.assertRaises(ClaimValidationError): validate_claims(self.card(claims,text),self.ctx)

    @patch.dict(os.environ,{'AZURE_OPENAI_ENDPOINT':'https://example.openai.azure.com','AZURE_OPENAI_API_KEY':'mock-key'})
    def test_rejected_real_path_uses_data_card_and_does_not_cache_bad_output(self):
        bad=self.card([dict(fact_id='home.shots',value='999')])
        with patch('backend.narrative.urlopen',return_value=FakeResponse(bad)):
            result=narrative.narrate(DEMO_GOAL)
        self.assertEqual(result['source'],'stats')
        self.assertEqual(result['fallback_reason'],'claim_validation_failed')
        self.assertEqual(result['verification']['status'],'blocked')
        self.assertNotIn('999',result['text'])
        self.assertFalse(narrative.CACHE)

    def test_injected_verification_demo_has_no_model_call(self):
        with patch('backend.narrative.urlopen') as model:
            result=verification_demo(DEMO_GOAL)
        model.assert_not_called()
        self.assertEqual(result['status'],'blocked')
        self.assertFalse(result['model_called'])
        self.assertEqual(len(result['issues']),2)


if __name__=='__main__': unittest.main()
