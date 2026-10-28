import unittest

from backend.engine import EVENTS, context, generate, state, stats, template, validate
from backend.match_clock import (HALF_TIME_START, SECOND_HALF_START, DURATION, DEMO_GOAL, DEMO_PRESS, clock_state, display_clock)


class EngineTests(unittest.TestCase):
    def test_reproducible_seed_and_valid_coordinates(self):
        self.assertEqual(EVENTS, generate(42))
        self.assertNotEqual(EVENTS, generate(43))
        validate(EVENTS)

    def test_early_window_has_no_future_events_or_stats(self):
        for second in [0, 9, 600, HALF_TIME_START, SECOND_HALF_START, DEMO_GOAL-1, DEMO_GOAL, DURATION]:
            snapshot = state(second)
            prefix = [e for e in EVENTS if e['second'] <= second]
            self.assertEqual(snapshot['stats'], stats(prefix))
            self.assertTrue(all(e['second'] <= second for e in snapshot['events']))
            self.assertTrue(all(e['second'] <= second for e in context(second)['evidence']))
            self.assertTrue(all(b['second'] <= second for b in snapshot['trend']))

    def test_goal_changes_score_only_when_it_happens(self):
        self.assertEqual(state(DEMO_GOAL-1)['stats']['home']['goals'] + 1, state(DEMO_GOAL)['stats']['home']['goals'])
        self.assertEqual(state(DEMO_GOAL-1)['stats']['away']['goals'], state(DEMO_GOAL)['stats']['away']['goals'])

    def test_navigation_uses_only_visible_events_and_corrected_outcomes(self):
        self.assertEqual(state(0)['navigation_events'],[])
        for second in [600,HALF_TIME_START,DEMO_GOAL-1,DEMO_GOAL,DURATION]:
            for revision in ['original','goal_removed']:
                nav=state(second,revision)['navigation_events']
                self.assertTrue(all(e['second']<=second for e in nav))
                self.assertEqual(len(nav),len({e['id'] for e in nav}))
        removed=next(e for e in state(DEMO_GOAL,'goal_removed')['navigation_events'] if e['second']==DEMO_GOAL)
        self.assertEqual(removed['outcome'],'disallowed')

    def test_rewind_is_independent_of_other_viewers(self):
        original = state(600)
        state(DURATION)
        self.assertEqual(state(600), original)

    def test_curated_chain_transfers_possession(self):
        chain = [e for e in EVENTS if DEMO_GOAL-45 <= e['second'] <= DEMO_GOAL]
        self.assertEqual([e['type'] for e in chain], ['pressure','pressure','pass','pass','pass','shot'])
        self.assertEqual(chain[0]['possession_id'], chain[2]['possession_id'])
        self.assertNotEqual(chain[2]['possession_id'], chain[3]['possession_id'])
        self.assertEqual(chain[3]['possession_id'], chain[5]['possession_id'])
        self.assertEqual(chain[2]['team'], 'away')
        self.assertEqual(chain[3]['team'], 'home')
        for previous, following in zip(chain, chain[1:]):
            self.assertEqual(previous['end'], following['start'])

    def test_empty_stats_and_different_audiences(self):
        self.assertIsNone(state(0)['stats']['home']['accuracy'])
        ctx = context(DEMO_GOAL)
        fan = template(ctx)
        analyst = template(ctx, mode='analyst')
        self.assertNotEqual(fan['text'], analyst['text'])
        self.assertIn('Last 5 min', analyst['text'])
        self.assertNotEqual(template(ctx, language='zh')['text'], fan['text'])
        self.assertTrue(set(fan['evidence_ids']) <= {e['id'] for e in ctx['evidence']})

    def test_metric_denominators(self):
        es = [dict(type='pass',team='home',outcome='complete'), dict(type='pass',team='home',outcome='incomplete'), dict(type='tackle',team='away',outcome='won')]
        summary = stats(es)
        self.assertEqual(summary['home']['accuracy'], 50)
        self.assertEqual(summary['away']['recoveries'], 2)
        self.assertEqual(summary['home']['recoveries'], 0)

    def test_recap_can_cite_prior_goals_without_future_leakage(self):
        ctx = context(DURATION, recap=True)
        goals = {e['id'] for e in EVENTS if e['outcome'] == 'goal'}
        self.assertTrue(goals <= {e['id'] for e in ctx['evidence']})
        self.assertLessEqual(len(ctx['evidence']), 8)
        early = context(DEMO_GOAL, recap=True)
        self.assertTrue(all(e['second'] <= DEMO_GOAL for e in early['evidence']))

    def test_clock_boundaries_and_real_half_time_interval(self):
        self.assertEqual(display_clock(2700), '45+0:00')
        self.assertEqual(display_clock(HALF_TIME_START-1), '45+1:59')
        self.assertEqual(clock_state(HALF_TIME_START)['match_status'], 'half_time')
        self.assertEqual(clock_state(SECOND_HALF_START-1)['match_status'], 'half_time')
        self.assertEqual(display_clock(SECOND_HALF_START), '45:00')
        self.assertEqual(display_clock(DURATION-1), '90+2:59')
        self.assertEqual(clock_state(DURATION)['match_status'], 'full_time')
        self.assertEqual(display_clock(DURATION), '90+3:00')
        self.assertTrue(all(e['type']=='substitution' and e['at_half_time'] for e in EVENTS if HALF_TIME_START < e['second'] < SECOND_HALF_START))
        a,b=state(HALF_TIME_START),state(SECOND_HALF_START-1)
        self.assertEqual(a['trend'],b['trend'])
        for side in ['home','away']:
            for metric in ['goals','shots','passes','pressures','fouls','offsides','red_cards']:
                self.assertEqual(a['stats'][side][metric],b['stats'][side][metric])
            self.assertEqual(b['lineups'][side]['substitutions'],1)
            self.assertEqual(b['lineups'][side]['windows'],0)

    def test_kickoffs_switch_ends_and_shots_follow_direction(self):
        kicks=[e for e in EVENTS if e['type']=='kickoff']
        self.assertEqual(kicks[0]['second'],0)
        second=next(e for e in kicks if e['second']==SECOND_HALF_START)
        self.assertEqual((kicks[0]['team'],second['team']),('home','away'))
        self.assertEqual(clock_state(0)['attacking_directions']['home'],-1)
        self.assertEqual(clock_state(SECOND_HALF_START)['attacking_directions']['home'],1)
        for e in EVENTS:
            if e['type']=='shot' and e['outcome']=='wide':
                self.assertTrue(e['end'][1]<44 or e['end'][1]>56)
            if e['type']=='shot' and e['outcome']!='blocked':
                direction=clock_state(e['second'])['attacking_directions'][e['team']]
                self.assertEqual(e['end'][0],100 if direction==1 else 0)

    def test_multi_seed_restarts_and_variable_event_cadence(self):
        kinds=set()
        for seed in range(100):
            events=generate(seed)
            validate(events)
            kinds.update(e['type'] for e in events)
            self.assertTrue(any(e['second']==DEMO_GOAL and e['outcome']=='goal' for e in events))
            for i,e in enumerate(events[:-1]):
                nxt=next((v for v in events[i+1:] if v['type'] not in ('card','substitution')),events[-1])
                if nxt['type'] in ('half_time','full_time','abandoned'):
                    continue
                if e['outcome']=='goal':
                    self.assertEqual(nxt['type'],'kickoff')
                    self.assertNotEqual(e['team'],nxt['team'])
                if e['type']=='shot' and e['outcome'] in ('wide','blocked','saved'):
                    self.assertEqual(nxt['type'],dict(wide='goal_kick',blocked='corner',saved='goalkeeper_release')[e['outcome']])
                if e['type']=='pressure':
                    self.assertEqual(e['start'],e['end'])
                    self.assertNotEqual(e['team'],e['possession_team'])
                if e['type']=='penalty':
                    self.assertEqual(nxt['type'],'shot')
                    self.assertEqual(nxt['set_piece'],'penalty')
        self.assertTrue({'free_kick','corner','throw_in','goal_kick','penalty'} <= kinds)
        gaps={b['second']-a['second'] for a,b in zip(EVENTS,EVENTS[1:]) if a['period']==b['period']}
        self.assertGreater(len(gaps),5)

    def test_second_half_windows_exclude_the_interval_without_future_leaks(self):
        ctx=context(SECOND_HALF_START+60)
        self.assertEqual(ctx['display_clock'],'46:00')
        self.assertIn('excluding',ctx['window_basis'])
        self.assertEqual(ctx['match_status'],'second_half')
        for moment in [HALF_TIME_START, SECOND_HALF_START, DEMO_GOAL, DURATION]:
            self.assertLessEqual(len(context(moment)['evidence']),8)
            self.assertTrue(all(e['second']<=moment for e in context(moment)['evidence']))


if __name__ == '__main__':
    unittest.main()
