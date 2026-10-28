"""Deterministic rule boundaries and prefix-only personnel state; no model calls."""
import copy
import unittest

from backend.football_rules import Roster, offside_offence
from backend.engine import EVENTS, generate, validate, lineups, state, context, template
from backend.match_clock import HALF_TIME_START, SECOND_HALF_START, DURATION


class OffsideTests(unittest.TestCase):
    def test_position_ball_second_last_and_own_half(self):
        self.assertTrue(offside_offence(85,70,[99,80,65]))
        self.assertFalse(offside_offence(80,70,[99,80,65]))  # level
        self.assertFalse(offside_offence(85,85,[99,80,65]))  # behind/level with ball
        self.assertFalse(offside_offence(50,30,[99,40,35]))  # own half
        self.assertFalse(offside_offence(85,70,[99,80,65],involved=False))

    def test_mirrored_direction_and_restart_exemptions(self):
        self.assertTrue(offside_offence(15,30,[1,20,35],-1))
        self.assertFalse(offside_offence(20,30,[1,20,35],-1))
        for kind in ['goal_kick','throw_in','corner']:
            self.assertFalse(offside_offence(85,70,[99,80,65],direct_restart=kind))
        self.assertTrue(offside_offence(85,70,[99,80,65],direct_restart='free_kick'))
        with self.assertRaises(ValueError):
            offside_offence(85,70,[99])

    def test_award_and_indirect_touch_are_consistent(self):
        calls=[i for i,e in enumerate(EVENTS) if e['type']=='offside']
        self.assertGreater(len(calls),0)
        for index in calls:
            e=EVENTS[index]
            self.assertEqual(EVENTS[index-1]['outcome'],'offside')
            following=[v for v in EVENTS[index+1:] if v['type'] not in ['card','substitution']]
            self.assertEqual(following[0]['type'],'indirect_free_kick')
            self.assertNotEqual(following[0]['team'],e['team'])
            self.assertEqual(following[0]['start'],e['end'])
            # Before a subsequent shot there must be a touch by another player.
            taker=following[0]['player_id']
            first_touch=next(v for v in following[1:] if v['type'] not in ['pressure','half_time','full_time'])
            self.assertFalse(first_touch['type']=='shot' and first_touch['player_id']==taker)
        call=EVENTS[calls[0]]
        self.assertEqual(state(call['second']-1)['stats'][call['team']]['offsides']+1,state(call['second'])['stats'][call['team']]['offsides'])
        self.assertEqual(context(call['second'])['kind'],'offside')


class RosterTests(unittest.TestCase):
    def test_caution_then_second_caution_and_dismissal(self):
        r=Roster()
        self.assertFalse(r.caution(2))
        self.assertEqual(len(r.active),11)
        self.assertTrue(r.caution(2))
        r.dismiss(2,'second_yellow')
        self.assertEqual(len(r.active),10)
        self.assertNotIn(2,r.active)
        for action in [lambda:r.caution(2),lambda:r.dismiss(2),lambda:r.substitute([(2,12)])]:
            with self.assertRaises(ValueError): action()
        r.substitute([(3,12)])
        self.assertEqual(len(r.active),10)

    def test_direct_red_keeper_and_minimum_seven(self):
        r=Roster()
        r.dismiss(0)
        self.assertIn(r.keeper,r.active)
        r.substitute([(r.keeper,11)])
        self.assertEqual(r.keeper,11)
        self.assertEqual(len(r.active),10)
        for p in [3,4,5]: r.dismiss(p)
        self.assertTrue(r.can_continue)
        r.dismiss(6)
        self.assertFalse(r.can_continue)

    def test_substitution_limits_batch_windows_and_no_reentry(self):
        r=Roster()
        r.substitute([(10,12)],half_time=True)
        self.assertEqual((r.substitutions,r.windows),(1,0))
        r.substitute([(9,13),(8,14)])
        r.substitute([(7,15)])
        r.substitute([(6,16)])
        self.assertEqual((r.substitutions,r.windows),(5,3))
        for changes in [[(5,17)],[(12,10)],[(10,18)]]:
            with self.assertRaises(ValueError): r.substitute(changes)
        self.assertEqual(len(r.active),11)
        windows=Roster()
        for a,b in [(10,12),(9,13),(8,14)]: windows.substitute([(a,b)])
        with self.assertRaises(ValueError): windows.substitute([(7,15)])
        windows.substitute([(7,15)],half_time=True)
        self.assertEqual(windows.windows,3)

    def test_batch_failure_is_atomic(self):
        for changes in [[(9,12),(8,12)],[(9,12),(9,13)],[(9,12),(30,13)],[(9,12),(8,9)],[]]:
            r=Roster(); before=copy.deepcopy(r.as_dict())
            with self.assertRaises(ValueError): r.substitute(changes)
            self.assertEqual(r.as_dict(),before)
        with self.assertRaises(ValueError): Roster().dismiss(2,'second_yellow')

    def test_prefix_rewind_dismissals_and_substitution_identity(self):
        red=next(e for e in EVENTS if e['type']=='card' and e['card_color']=='red')
        side=red['team']
        before=state(red['second']-1)
        after=state(red['second'])
        self.assertEqual(len(before['lineups'][side]['active']),11)
        self.assertEqual(len(after['lineups'][side]['active']),10)
        self.assertNotIn(red['player_id'],[p['id'] for p in after['lineups'][side]['active']])
        state(DURATION)
        self.assertEqual(state(red['second']-1),before)
        self.assertIn('10 players',template(context(red['second']))['text'])
        for e in EVENTS:
            if e['type']!='substitution': continue
            a,b=state(e['second']-1)['lineups'][e['team']],state(e['second'])['lineups'][e['team']]
            self.assertIn(e['player_id'],[p['id'] for p in a['active']])
            self.assertNotIn(e['player_id'],[p['id'] for p in b['active']])
            self.assertIn(e['incoming_player_id'],[p['id'] for p in b['active']])
            self.assertEqual(len(a['active']),len(b['active']))
        for r in state(DURATION)['lineups'].values():
            self.assertEqual((r['substitutions'],r['windows']),(5,3))

    def test_one_hundred_seeds_keep_all_actors_eligible(self):
        reasons=set()
        for seed in range(100):
            events=generate(seed)
            validate(events)  # replays every actor and recipient against the current roster
            reasons.update(e['card_reason'] for e in events if e['type']=='card' and e['card_color']=='red')
            last=lineups(events)
            for side,r in last.items():
                self.assertLessEqual(r['substitutions'],5)
                self.assertLessEqual(r['windows'],3)
                self.assertEqual(len(r['active']),11-len(r['dismissed']))
                self.assertFalse(set(p['id'] for p in r['active']) & set(p['id'] for p in r['withdrawn']+r['dismissed']))
        self.assertTrue({'second_yellow','serious_foul_play'} <= reasons)


if __name__=='__main__': unittest.main()
