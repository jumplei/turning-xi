"""Seeded football event simulation. Coordinates are physical pitch locations, not tracking."""
import random

from .revisions import view_events, revision_info

from .football_rules import Roster, offside_offence

from .match_clock import (HALF_TIME_START, SECOND_HALF_START, DURATION, DEMO_PRESS, DEMO_GOAL,
                          PLAYING_DURATION, HALF_TIME_BREAK, clock_state, display_clock, playing_second)

TEAMS = {
    'home': {'name': 'Northbridge FC', 'short': 'NBR', 'color': '#baff5a'},
    'away': {'name': 'Harbour Athletic', 'short': 'HBA', 'color': '#a9b8ff'},
}
PLAYERS = {
    'home': ['A. Cole', 'J. Silva', 'M. Reed', 'L. Park', 'D. Okafor', 'E. Chen', 'T. Mason', 'R. Costa', 'N. Ali', 'S. Blake', 'K. Ito'],
    'away': ['O. Price', 'F. Santos', 'H. Kim', 'I. Novak', 'B. Diallo', 'C. Evans', 'Y. Mori', 'G. Rossi', 'P. Khan', 'V. James', 'W. Lin'],
}
PLAYERS['home'] += ['M. Arden', 'L. Vale', 'P. Rowan', 'C. Hart', 'F. West', 'I. Stone', 'B. Finch', 'U. Lane', 'G. Frost']
PLAYERS['away'] += ['D. Ash', 'N. Brook', 'J. Dale', 'S. Fox', 'A. Heath', 'R. Lake', 'T. Moon', 'E. Pine', 'L. Shore']
DATASET_VERSION = '3.0'

STYLES = {'home': dict(accuracy=.85, press=.17), 'away': dict(accuracy=.83, press=.13)}


def other(team):
    return 'away' if team == 'home' else 'home'


def generate(seed=42):
    rng = random.Random(seed)
    rule_rng = random.Random('rules:%s' % seed)
    rosters = {side: Roster() for side in TEAMS}
    indirect_pending = None
    demo_cautions = 0
    protected_away = 2  # labelled two-caution storyline, kept available until its second caution
    sub_slots = {side: 0 for side in TEAMS}
    events, possession = [], 0
    team, ball, holder = 'home', [50, 50], 9
    period = 1

    class MatchEnded(Exception):
        pass

    def direction(side):
        return (-1 if side == 'home' else 1) * (1 if period == 1 else -1)

    def add(t, kind, side=None, start=None, end=None, outcome='played', player=None, **extra):
        events.append(dict(id='evt_%04d' % (len(events) + 1), second=t, period=period,
                           clock=display_clock(t), playing_second=playing_second(t), type=kind,
                           team=side, possession_team=team if side else None,
                           possession_id='pos_%04d' % possession,
                           player_id=side[0].upper() + str(player + 1).zfill(2) if side else None,
                           player=PLAYERS[side][player] if side else None,
                           start=start[:] if start else None, end=end[:] if end else None,
                           outcome=outcome, scripted=extra.pop('scripted', False), **extra))

    def actor(side, preferred=None):
        candidates = rosters[side].outfield
        if preferred in candidates:
            return preferred
        return rng.choice(candidates)

    def card(t, side, player, color, reason, scripted=False):
        if color == 'yellow':
            second = rosters[side].caution(player)
        else:
            second = False
            rosters[side].dismiss(player, reason)
        add(t, 'card', side, ball, ball, color, player, card_color=color, card_reason=reason, scripted=scripted)
        if second:
            rosters[side].dismiss(player, 'second_yellow')
            add(t+1, 'card', side, ball, ball, 'red', player, card_color='red', card_reason='second_yellow', scripted=scripted)
            return t+1
        return t

    def substitute_batch(t, side, count, half_time=False):
        nonlocal holder
        roster = rosters[side]
        # The reserve keeper is available, but the scripted substitutions use outfield players.
        eligible = [p for p in roster.outfield if not (side == 'away' and p == protected_away and demo_cautions < 2)]
        changes = list(zip(sorted(eligible, reverse=True)[:count], sorted(roster.bench - {11})[:count]))
        if not changes:
            return t
        window_id = 'ht' if half_time else '%s_window_%s' % (side, roster.windows+1)
        roster.substitute(changes, half_time=half_time)
        for offset,(off,on) in enumerate(changes):
            add(t+offset, 'substitution', side, None, None, 'replaced', off,
                incoming_player_id=side[0].upper()+str(on+1).zfill(2), incoming_player=PLAYERS[side][on],
                substitution_window=window_id, at_half_time=half_time, scripted=True)
            if team == side and holder == off:
                holder = on
        return t+len(changes)-1

    def stoppage(resume_at):
        nonlocal demo_cautions
        slot = events[-1]['second']+1 if events else resume_at
        # Two dissent cautions at existing stoppages do not change the awarded restart.
        due = 1800 if demo_cautions == 0 else SECOND_HALF_START+1800
        if demo_cautions < 2 and max(slot,due)+2 < resume_at:
            slot=max(slot,due)
            card(slot, 'away', protected_away, 'yellow', 'dissent', True)
            demo_cautions += 1
            slot = events[-1]['second']+1
        times = [SECOND_HALF_START+1200, SECOND_HALF_START+1620, SECOND_HALF_START+2220]
        for side in TEAMS:
            n = sub_slots[side]
            count = [2,1,1][n] if n < 3 else 0
            if n < 3 and max(slot,times[n])+count < resume_at:
                slot=max(slot,times[n])
                slot = substitute_batch(slot, side, count)+1
                sub_slots[side] += 1

    def claim(side, player=None):
        nonlocal team, holder, possession, indirect_pending
        team, holder = side, actor(side, player)
        if player == rosters[side].keeper:
            holder = player
        indirect_pending = None
        possession += 1

    def restart(t, kind, side, origin, destination=None):
        nonlocal ball, holder, indirect_pending
        stoppage(t)
        if any(not r.can_continue for r in rosters.values()):
            add(events[-1]['second']+1, 'abandoned', outcome='insufficient_players')
            raise MatchEnded
        # The award is a new possession even when the same team retains the restart.
        claim(side, rosters[side].keeper if kind == 'goal_kick' else 9)
        end = destination[:] if destination else origin[:]
        add(t, kind, side, origin, end, 'restart', holder)
        ball = end
        indirect_pending = side if kind == 'indirect_free_kick' else None
        if kind in ('corner', 'throw_in', 'goal_kick'):
            holder = actor(side)

    def shot(t, end_time, penalty=False):
        nonlocal ball, holder
        side, player = team, holder
        start = ball[:]
        # A deliberately simple chance process, not a trained or calibrated xG model.
        chance = .72 if penalty else .06 * len(rosters[side].active)/len(rosters[other(side)].active)
        outcome = 'goal' if rng.random() < chance else rng.choices(['saved', 'wide', 'blocked'], [4, 4, 2])[0]
        goal_x = 100 if direction(side) == 1 else 0
        end = [goal_x, 50] if outcome == 'goal' else [goal_x, round(rng.uniform(45, 55), 1)]
        if outcome == 'wide':
            end[1] = round(15+(end[1]-45)*28/5 if end[1]<50 else 57+(end[1]-50)*28/5, 1)
        if outcome == 'blocked':
            end = [round(max(0, min(100, start[0] + direction(side) * 2)), 1), start[1]]
        add(t, 'shot', side, start, end, outcome, player, set_piece='penalty' if penalty else None,
            under_pressure=not penalty and rng.random() < .35)
        ball = end
        delay = rng.randint(18, 32)
        if t + delay >= end_time:
            return end_time
        if outcome == 'goal':
            restart(t + delay, 'kickoff', other(side), [50, 50])
        elif outcome == 'saved':
            claim(other(side), rosters[other(side)].keeper)
            end = [25 if goal_x == 0 else 75, round(rng.uniform(30, 70), 1)]
            add(t+delay, 'goalkeeper_release', team, ball, end, 'complete', holder)
            ball = end
            holder = actor(team)
        elif outcome == 'wide':
            restart(t + delay, 'goal_kick', other(side), [goal_x, 50], [7 if goal_x == 0 else 93, 50])
        else:
            restart(t + delay, 'corner', side, [goal_x, 0], [8 if goal_x == 0 else 92, round(rng.uniform(30, 70), 1)])
        return t + delay

    def curated():
        nonlocal ball, holder
        t = DEMO_PRESS
        # Establish away possession without teleporting the ball, then a legal free kick.
        if team == 'home':
            claim('away', 3)
            add(t, 'tackle', 'away', ball, ball, 'won', holder)
            add(t+2, 'pass', 'away', ball, [65, 38], 'complete', holder)
        else:
            add(t, 'pass', 'away', ball, [65, 38], 'complete', holder)
        ball, holder = [65, 38], actor('away', 3)
        add(t+5, 'foul', 'home', ball, ball, 'committed', actor('home',4), restart_type='free_kick')
        restart(t+10, 'free_kick', 'away', ball)
        for offset in (15, 20):
            add(t+offset, 'pressure', 'home', ball, ball, 'applied', actor('home',8))
        end = [70, 40]
        add(t+30, 'pass', 'away', ball, end, 'incomplete', holder, under_pressure=True)
        ball = end
        claim('home', 4)
        for offset, end, recipient in [(40, [82, 45], 7), (50, [90, 50], 3)]:
            add(t+offset, 'pass', 'home', ball, end, 'complete', holder)
            ball, holder = end, actor('home',recipient)
        add(DEMO_GOAL, 'shot', 'home', ball, [100, 50], 'goal', holder, under_pressure=False)
        ball = [100, 50]
        restart(DEMO_GOAL+25, 'kickoff', 'away', [50, 50])
        for e in events:
            if DEMO_PRESS <= e['second'] <= DEMO_GOAL+25:
                e['scripted'] = True
                e['phase'] = 'press'
        return DEMO_GOAL+25

    try:
        for period, begin, end_time, kicking_side in [(1, 0, HALF_TIME_START, 'home'),
                                                      (2, SECOND_HALF_START, DURATION, 'away')]:
            if any(not r.can_continue for r in rosters.values()):
                break
            restart(begin, 'kickoff', kicking_side, [50, 50])
            t = begin
            while True:
                nxt = t + rng.randint(2, 7)
                if period == 2 and t < DEMO_PRESS <= nxt:
                    t = curated()
                    continue
                if nxt >= end_time:
                    break
                t = nxt
                if any(not r.can_continue for r in rosters.values()):
                    add(t, 'abandoned', outcome='insufficient_players')
                    return events
                side, defend = team, other(team)
                press_rate = STYLES[defend]['press'] * len(rosters[defend].active)/11
                p = rng.random()
                attack_distance = 100-ball[0] if direction(side) == 1 else ball[0]
                if p < press_rate:
                    add(t, 'pressure', defend, ball, ball, 'applied', actor(defend))
                elif p < press_rate + .045:
                    claim(defend)
                    add(t, 'tackle', defend, ball, ball, 'won', holder)
                elif p < press_rate + .075 and t+18 < end_time and not (period == 2 and t < DEMO_PRESS <= t+60):
                    # No foul-in-the-box approximation: an actual penalty restart is used there.
                    penalty = attack_distance < 16 and 20 <= ball[1] <= 80
                    if penalty and rng.random() > .08:
                        add(t, 'pressure', defend, ball, ball, 'applied', actor(defend))
                        continue
                    offender = actor(defend)
                    if defend=='away' and offender==protected_away:
                        offender=rule_rng.choice([p for p in rosters[defend].outfield if p!=protected_away])
                    add(t, 'foul', defend, ball, ball, 'committed', offender,
                        restart_type='penalty' if penalty else 'free_kick')
                    sanction=rule_rng.random()
                    if sanction<.015:
                        card(t+1, defend, offender, 'red', 'serious_foul_play')
                    elif sanction<.17:
                        card(t+1, defend, offender, 'yellow', 'reckless_challenge')
                    if not rosters[defend].can_continue:
                        add(events[-1]['second']+1, 'abandoned', outcome='insufficient_players')
                        validate(events)
                        return events
                    if penalty:
                        origin = [89.5 if direction(side) == 1 else 10.5, 50]
                        restart(t+12, 'penalty', side, origin)
                        t = shot(t+18, min(end_time, DEMO_PRESS) if period == 2 and t < DEMO_PRESS else end_time, True)
                    else:
                        restart(t+12, 'free_kick', side, ball)
                        t += 12
                elif indirect_pending is None and attack_distance < 24 and .25 <= p < .40 and not (period == 2 and t < DEMO_PRESS <= t+60):
                    t = shot(t, min(end_time, DEMO_PRESS) if period == 2 and t < DEMO_PRESS else end_time)
                else:
                    start = ball[:]
                    if rng.random() < .025 and t+12 < end_time and not (period == 2 and t < DEMO_PRESS <= t+12):
                        end = [ball[0], rng.choice([0, 100])]
                        add(t, 'pass', side, start, end, 'out', holder)
                        restart(t+12, 'throw_in', defend, end, [end[0], 5 if end[1] == 0 else 95])
                        t += 12
                    else:
                        end = [round(max(3, min(97, ball[0]+direction(side)*rng.uniform(-12, 20))), 1),
                               round(max(5, min(95, ball[1]+rng.uniform(-17, 17))), 1)]
                        complete = rng.random() < STYLES[side]['accuracy']-.015*(11-len(rosters[side].active))
                        receiver = rng.choice([i for i in rosters[side].outfield if i != holder])
                        # Synthetic positions at the instant of the pass, not continuous player tracking.
                        ball_progress = start[0] if direction(side)==1 else 100-start[0]
                        line = min(97, max(60, ball_progress+rule_rng.uniform(14,28)))
                        opponent_x = [99.0 if i==rosters[defend].keeper else round(max(5,line-rule_rng.uniform(0,25)),1) for i in sorted(rosters[defend].active)]
                        opponent_x = opponent_x if direction(side)==1 else [100-x for x in opponent_x]
                        receiver_at_pass = round(max(0,min(100,end[0]-direction(side)*rule_rng.uniform(0,12))),1)
                        snapshot = dict(ball_x=start[0], receiver_x=receiver_at_pass, receiver_y=end[1], opponent_x=opponent_x, direction=direction(side), involved=complete)
                        offside = complete and offside_offence(receiver_at_pass,start[0],opponent_x,direction(side))
                        # Reserve time for the whistle and indirect free kick.
                        if offside and (t+12>=end_time or period==2 and t<DEMO_PRESS<=t+12):
                            end=start[:]
                            snapshot['receiver_x']=end[0]
                            offside=False
                        add(t, 'pass', side, start, end, 'offside' if offside else 'complete' if complete else 'incomplete', holder,
                            recipient_id=side[0].upper()+str(receiver+1).zfill(2), recipient=PLAYERS[side][receiver], pass_snapshot=snapshot)
                        ball = end
                        if offside:
                            add(t+1, 'offside', side, ball, ball, 'penalised', receiver, pass_event_id=events[-1]['id'], pass_snapshot=snapshot)
                            restart(t+12, 'indirect_free_kick', defend, ball)
                            t += 12
                        elif complete:
                            holder = receiver
                            indirect_pending = None  # a different teammate has now touched the ball
                        else:
                            claim(defend)
            add(end_time, 'half_time' if period == 1 else 'full_time', outcome='whistle')
            if period==1:
                substitute_batch(end_time+1,'home',1,True)
                substitute_batch(end_time+2,'away',1,True)
    except MatchEnded:
        pass
    validate(events)
    return events


def player_index(player_id):
    return int(player_id[1:])-1


def apply_roster_event(rosters, seen_windows, e):
    if e['team'] is None:
        return
    side=e['team']
    r=rosters[side]
    player=player_index(e['player_id'])
    if e['type']=='card':
        if e['card_color']=='yellow':
            r.caution(player)
        else:
            r.dismiss(player,e['card_reason'])
    elif e['type']=='substitution':
        key=(side,e['substitution_window'])
        r.substitute([(player,player_index(e['incoming_player_id']))], half_time=e['at_half_time'] or key in seen_windows)
        seen_windows.add(key)


def lineups(events):
    rosters={side:Roster() for side in TEAMS}
    seen=set()
    for e in events:
        apply_roster_event(rosters,seen,e)
    def describe(side,player,r):
        return dict(id=side[0].upper()+str(player+1).zfill(2), number=player+1, name=PLAYERS[side][player],
                    yellow_cards=r.cautions.get(player,0), sent_off=player in r.dismissed,
                    goalkeeper=player==r.keeper, dismissal_reason=r.dismissal_reasons.get(player))
    return {side:dict(active=[describe(side,p,r) for p in sorted(r.active)],
                      bench=[describe(side,p,r) for p in sorted(r.bench)],
                      withdrawn=[describe(side,p,r) for p in sorted(r.withdrawn)],
                      dismissed=[describe(side,p,r) for p in sorted(r.dismissed)],
                      substitutions=r.substitutions, windows=r.windows,
                      substitutions_remaining=5-r.substitutions, windows_remaining=3-r.windows)
            for side,r in rosters.items()}


def validate(events):
    assert len({e['id'] for e in events}) == len(events)
    prior=-1
    rosters={side:Roster() for side in TEAMS}
    seen_windows=set()
    seen_window_end={}
    for index,e in enumerate(events):
        assert e['second']>prior
        prior=e['second']
        assert 0<=e['second']<=DURATION
        if HALF_TIME_START<e['second']<SECOND_HALF_START:
            assert e['type']=='substitution' and e['at_half_time']
        assert e['period']==(1 if e['second']<SECOND_HALF_START else 2)
        assert e['clock']==display_clock(e['second'])
        if e['team'] is None:
            assert e['type'] in ('half_time','full_time','abandoned') and e['player'] is None
        else:
            side=e['team']
            assert side in TEAMS and e['player'] in PLAYERS[side]
            assert e['player_id']==side[0].upper()+str(PLAYERS[side].index(e['player'])+1).zfill(2)
            assert player_index(e['player_id']) in rosters[side].active
            if e['type']!='substitution':
                assert all(0<=v<=100 for k in ('start','end') for v in e[k])
            if e.get('recipient_id'):
                assert player_index(e['recipient_id']) in rosters[side].active
                assert e['recipient_id']!=e['player_id']
            if e['type']=='substitution':
                assert e['at_half_time']==(HALF_TIME_START<e['second']<SECOND_HALF_START)
                key=(side,e['substitution_window'])
                if key in seen_window_end:
                    assert seen_window_end[key]==index-1, 'A substitution window cannot be reused after play resumes'
                seen_window_end[key]=index
            apply_roster_event(rosters,seen_windows,e)
        assert e['outcome']!='goal' or e['type']=='shot'
        if e['type']=='shot':
            target=0 if (e['team']=='home')==(e['period']==1) else 100
            if e['outcome']!='blocked':
                assert e['end'][0]==target
        if e['type']=='offside':
            snap=e['pass_snapshot']
            assert offside_offence(snap['receiver_x'],snap['ball_x'],snap['opponent_x'],snap['direction'],involved=snap['involved'])
            assert events[index-1]['id']==e['pass_event_id'] and events[index-1]['outcome']=='offside'
        if e['type']=='card' and e['card_color']=='yellow' and rosters[e['team']].cautions[player_index(e['player_id'])]==2:
            nxt=events[index+1]
            assert nxt['type']=='card' and nxt['card_color']=='red' and nxt['card_reason']=='second_yellow'
            assert nxt['player_id']==e['player_id']
        if any(not r.can_continue for r in rosters.values()):
            assert e['type']=='abandoned' or index+1<len(events) and events[index+1]['type']=='abandoned'
    for index,e in enumerate(events[:-1]):
        if e['type'] not in ('foul','offside','shot') and not (e['type']=='pass' and e['outcome']=='out'):
            continue
        following=next((v for v in events[index+1:] if v['type'] not in ('card','substitution')),None)
        if not following or following['type'] in ('half_time','full_time','abandoned'):
            continue
        if e['outcome']=='goal':
            assert following['type']=='kickoff' and following['team']==other(e['team'])
            assert following['start']==[50,50]
        if e['type']=='foul':
            assert following['type']==e['restart_type'] and following['team']==other(e['team'])
        if e['type']=='offside':
            assert following['type']=='indirect_free_kick' and following['team']==other(e['team'])
        if e['type']=='pass' and e['outcome']=='out':
            assert following['type']=='throw_in' and following['team']==other(e['team'])


EVENTS = generate()

def stats(events):
    result = {}
    for side in TEAMS:
        es = [e for e in events if e['team'] == side]
        passes = [e for e in es if e['type'] == 'pass']
        complete = sum(e['outcome'] == 'complete' for e in passes)
        result[side] = dict(goals=sum(e['outcome'] == 'goal' for e in es),
                            shots=sum(e['type'] == 'shot' and e['outcome']!='disallowed' for e in es),
                            yellow_cards=sum(e['type']=='card' and e['card_color']=='yellow' for e in es),
                            red_cards=sum(e['type']=='card' and e['card_color']=='red' for e in es),
                            offsides=sum(e['type']=='offside' for e in es),
                            substitutions=sum(e['type']=='substitution' for e in es),
                            on_target=sum(e['type'] == 'shot' and e['outcome'] in ('goal','saved') for e in es),
                            fouls=sum(e['type'] == 'foul' for e in es),
                            corners=sum(e['type'] == 'corner' for e in es),
                            passes=len(passes), complete=complete,
                            accuracy=round(complete / len(passes) * 100, 1) if passes else None,
                            pressures=sum(e['type'] == 'pressure' for e in es),
                            recoveries=sum((e['type'] == 'tackle' and e['team'] == side) or
                                           (e['type'] == 'pass' and e['outcome'] == 'incomplete' and e['team'] != side)
                                           for e in events))
    return result


def state(second, revision='original'):
    visible = view_events(EVENTS,second,revision)
    now = playing_second(second)
    current = [e for e in visible if now - 300 < e['playing_second'] <= now]
    previous = [e for e in visible if now - 600 < e['playing_second'] <= now - 300]
    trend = []
    for start in range(0, now, 300):
        end = min(start + 300, now)
        block = stats([e for e in visible if start < e['playing_second'] <= end])
        elapsed = end if end <= HALF_TIME_START else end + HALF_TIME_BREAK
        trend.append(dict(second=elapsed, playing_second=end, home=block['home']['pressures'],
                          away=block['away']['pressures'], complete=end == start+300))
    clock=clock_state(second)
    if any(e['type']=='abandoned' for e in visible):
        clock['match_status']='abandoned'
    return dict(second=second, revision=revision_info(second,revision), **clock, lineups=lineups(visible), stats=stats(visible), recent_stats=stats(current),
                previous_stats=stats(previous), events=visible[-12:][::-1], trend=trend,
                navigation_events=[{k:e.get(k) for k in ['id','second','type','team','player','outcome','card_reason']}
                                   for e in visible if e['type'] in ('card','offside','substitution','half_time','full_time')
                                   or e['type']=='kickoff' and e['second']==SECOND_HALF_START
                                   or e['type']=='shot' and e['outcome'] in ('goal','disallowed')],
                event_count=len(visible), window_basis='playing time, excluding the half-time interval')


def context(second, focus='neutral', recap=False, revision='original'):
    s = state(second,revision)
    visible = view_events(EVENTS,second,revision)
    recent = [e for e in visible if s['playing_second'] - 300 < e['playing_second'] and e['team']]
    pressure=[e for e in recent if e['type']=='pressure']
    significant=[e for e in recent if e['type'] in ('shot','card','offside','substitution') and e['outcome']!='disallowed']
    target=significant[-1] if significant else None
    if target:
        kind={'card':'discipline','offside':'offside','substitution':'substitution'}.get(target['type'], 'goal' if target['outcome']=='goal' else 'chance')
    else:
        kind='pressure' if len(pressure)>=3 else 'rhythm'
    # At most eight prefix-only events surrounding the latest significant event.
    if target:
        evidence = [e for e in recent if target['second'] - 70 <= e['second'] <= target['second']][-8:]
    else:
        evidence = recent[-8:]
    if recap:
        # Match-wide stories need goals and dismissals, not only the latest window.
        goal_events = [e for e in visible if e['outcome'] == 'goal'][-8:]
        slots=8-len(goal_events)
        dismissals=[e for e in visible if e['type']=='card' and e.get('card_color')=='red']
        key_events=goal_events+(dismissals[-slots:] if slots else [])
        if s['match_status']=='full_time':
            target=next((e for e in reversed(visible) if e['type']=='full_time'),target)
            kind='full_time'
            if target and len(key_events)<8:key_events.append(target)
        seen = {e['id'] for e in key_events}
        additional = [e for e in evidence if e['id'] not in seen]
        slots = 8 - len(key_events)
        evidence = sorted(key_events + (additional[-slots:] if slots else []), key=lambda e:e['second'])
    return dict(second=second, revision=s['revision'], match_status=s['match_status'], display_clock=s['display_clock'], period=s['period'], kind=kind, target=target, focus=focus, teams=TEAMS,
                stats=s['stats'], recent_stats=s['recent_stats'], previous_stats=s['previous_stats'],
                goals=[dict(event_id=e['id'],second=e['second'], clock=e['clock'], team=e['team'], player=e['player']) for e in visible if e['outcome'] == 'goal'],
                personnel={side:dict(on_pitch=len(r['active']),substitutions=r['substitutions'],windows=r['windows'],dismissed=r['dismissed']) for side,r in s['lineups'].items()},
                window_seconds=300, window_basis=s['window_basis'], evidence=evidence,
                discipline_events=[{k:e[k] for k in ('id','second','clock','player_id','player','team','card_color','card_reason')} for e in visible if e['type']=='card'])


def template(ctx, mode='fan', language='en', recap=False):
    zh = language == 'zh'
    kind = ctx['kind']
    titles = {'goal': ('The finish, and the build-up', '进球背后的进攻过程'),
              'chance': ('A chance worth a closer look', '一次值得回看的机会'),
              'pressure': ('The pressure is building', '压迫正在升温'),
              'rhythm': ('Reading the rhythm', '解读比赛节奏'),
              'discipline': ('Discipline changes the picture', '纪律事件改变场上局面'),
              'offside': ('The run was ahead of the line', '这次跑动越过了越位线'),
              'substitution': ('Fresh players enter the match', '替补球员登场')}
    evidence = ctx['evidence']
    shot = next((e for e in reversed(evidence) if e['type'] == 'shot' and e['outcome']!='disallowed'), None)
    focus = ctx['focus'] if ctx['focus'] != 'neutral' else (shot['team'] if shot else 'home')
    name = TEAMS[focus]['name']
    a, b = ctx['recent_stats'][focus], ctx['previous_stats'][focus]
    score = '%s–%s' % (ctx['stats']['home']['goals'], ctx['stats']['away']['goals'])
    if recap or ctx['match_status']=='full_time':
        title = ('全场回顾' if zh else 'Full-time recap') if ctx['match_status'] == 'full_time' else ('比赛阶段回顾' if zh else 'The match so far')
        text = ('截至当前，比分为 %s。%s 完成 %s 次射门；关联事件包含进球及最近片段。' % (score, name, ctx['stats'][focus]['shots'])) if zh else ('The score is %s. %s have taken %s shots so far. The linked evidence includes goals and recent play.' % (score, name, ctx['stats'][focus]['shots']))
        if ctx['goals']:
            last = ctx['goals'][-1]
            text += (' 最近一次进球来自 %s，由 %s 在 %s 完成。' % (TEAMS[last['team']]['name'], last['player'], last['clock'])) if zh else (' The latest goal came from %s: %s at %s.' % (TEAMS[last['team']]['name'], last['player'], last['clock']))
        if ctx['match_status'] == 'full_time':
            h, a_score = ctx['stats']['home']['goals'], ctx['stats']['away']['goals']
            result = ('双方战平。' if zh else 'The match ended in a draw.') if h == a_score else ((TEAMS['home' if h > a_score else 'away']['name'] + ' 获胜。') if zh else (TEAMS['home' if h > a_score else 'away']['name'] + ' won the match.'))
            text = ('全场比分 %s。' % score if zh else 'Full time: %s. ' % score) + result + ' ' + text
    else:
        title = titles[kind][int(zh)]
        if shot:
            text = ('%s 在 %s 完成%s。回看此前的传球与球权转换，可以看到机会形成的过程。' % (TEAMS[shot['team']]['name'], shot['clock'], '进球' if shot['outcome']=='goal' else '射门')) if zh else ('%s %s at %s. The linked passes and possession changes show how the opportunity developed.' % (TEAMS[shot['team']]['name'], 'scored' if shot['outcome']=='goal' else 'took a shot', shot['clock']))
            pressures = [e for e in evidence if e['type'] == 'pressure' and e['team'] == shot['team']]
            turnovers = [e for e in evidence if e['type'] == 'pass' and e['outcome'] == 'incomplete' and e['team'] != shot['team']]
            if pressures and turnovers:
                text += (' 片段中，%s 次压迫之后出现对手传球失误，再形成射门；这是一条可观察的事件链，不能单独证明因果关系。' % len(pressures)) if zh else (' In this sequence, %s pressure events precede an intercepted opposition pass and the shot: an observable chain, rather than proof of causation.' % len(pressures))
        else:
            text = ('%s 最近五分钟出现 %s 次压迫事件，前五分钟为 %s 次。这描述了比赛中的施压活动，不能单独证明战术因果。' % (name, a['pressures'], b['pressures'])) if zh else ('%s recorded %s pressure events in the last five minutes, compared with %s in the previous window. This describes pressing activity; it does not establish tactical causation.' % (name, a['pressures'], b['pressures']))
    target=ctx.get('target')
    if not recap and target and kind=='discipline':
        side=target['team']
        if target['card_color']=='red':
            reason=('两黄变一红' if zh else 'a second caution') if target['card_reason']=='second_yellow' else ('直接红牌' if zh else 'a direct red card')
            count=11-ctx['stats'][side]['red_cards']
            text=('%s 因%s被罚下。%s 目前场上有 %s 人。' % (target['player'],reason,TEAMS[side]['name'],count)) if zh else ('%s was sent off following %s. %s now have %s players on the pitch.' % (target['player'],reason,TEAMS[side]['name'],count))
        else:
            text=('%s 收到一张黄牌。这次警告不会减少场上人数；同场再次被警告将被罚下。' % target['player']) if zh else ('%s received a caution. A yellow card does not reduce the side; another caution in this match would mean a sending-off.' % target['player'])
    elif not recap and target and kind=='offside':
        text=('%s 接球参与进攻时被判越位，对方获得间接任意球。依据传球瞬间的合成位置快照，不是视频判罚。' % target['player']) if zh else ('%s was penalised for offside on receiving the pass. The opponents receive an indirect free kick. The decision uses a synthetic snapshot at the pass, not video tracking.' % target['player'])
    elif not recap and target and kind=='substitution':
        text=('%s 换下 %s，换上 %s，已使用 %s/5 个换人名额。' % (TEAMS[target['team']]['name'],target['player'],target['incoming_player'],ctx['stats'][target['team']]['substitutions'])) if zh else ('%s replaced %s with %s and have used %s of five substitutions.' % (TEAMS[target['team']]['name'],target['player'],target['incoming_player'],ctx['stats'][target['team']]['substitutions']))
    if ctx['match_status'] == 'half_time' and not recap:
        title = '中场休息' if zh else 'Half-time interval'
        text = ('中场比分 %s。下半场将在换边后从 45:00 开始。' % score) if zh else ('The half-time score is %s. Play resumes at 45:00 with the teams changing ends.' % score)
    if mode == 'analyst':
        acc = '—' if a['accuracy'] is None else str(a['accuracy']) + '%'
        text += (' 最近五分钟：%s 传球 %s/%s，成功率 %s，射门 %s 次。窗口为比赛时间，数据来自合成事件。' % (name, a['complete'], a['passes'], acc, a['shots'])) if zh else (' Last 5 min: %s completed %s/%s passes (%s), with %s %s. Windows exclude the half-time break; all metrics are computed from synthetic events.' % (name, a['complete'], a['passes'], acc, a['shots'], 'shot' if a['shots'] == 1 else 'shots'))
    elif ctx['focus'] != 'neutral':
        text += (' 关注球队：%s。' % name) if zh else (' Following %s.' % name)
    return dict(title=title, text=text, evidence_ids=[e['id'] for e in evidence])
