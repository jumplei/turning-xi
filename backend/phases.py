"""Explicit event heuristics, not causal or tactical tracking inference."""
from .engine import EVENTS, TEAMS, other, stats, context
from .revisions import view_events, revision_info

LABELS = {'goal_build_up':'Goal build-up', 'recovery_to_shot':'Recovery to shot',
          'sustained_pressure':'Sustained pressure', 'goal_moment':'Goal moment'}


def detect_phases(second, revision='original'):
    events=view_events(EVENTS,second,revision)
    phases=[]
    pressure_keys=set()
    for i,e in enumerate(events):
        side=e['team']
        if not side: continue
        window=[v for v in events[max(0,i-22):i+1] if v['period']==e['period'] and e['second']-75<=v['second']]
        chain=[]; kind=None
        if e['type']=='pressure':
            pressures=[v for v in window if v['type']=='pressure' and v['team']==side and v['possession_id']==e['possession_id'] and e['second']-v['second']<=30]
            key=(side,e['possession_id'])
            if len(pressures)>=3 and key not in pressure_keys:
                chain=pressures[-3:];kind='sustained_pressure';pressure_keys.add(key)
        elif e['type']=='shot' and e['outcome']!='disallowed':
            same=[v for v in window if v['possession_id']==e['possession_id'] and v['type'] in ('pass','shot') and v['team']==side]
            passes=[v for v in same if v['type']=='pass' and v['outcome']=='complete']
            first=same[0] if same else e
            recoveries=[v for v in window if v['second']<=first['second'] and
                        ((v['type']=='tackle' and v['team']==side and v['outcome']=='won') or
                         (v['type']=='pass' and v['team']==other(side) and v['outcome']=='incomplete'))]
            recovery=recoveries[-1] if recoveries else None
            if recovery and passes and first['second']-recovery['second']<=15:
                pressures=[v for v in window if v['type']=='pressure' and v['team']==side and 0<=recovery['second']-v['second']<=25]
                chain=pressures[-2:]+[recovery]+same[-5:];kind='recovery_to_shot'
            elif e['outcome']=='goal':
                chain=same[-8:];kind='goal_build_up' if len(passes)>=2 else 'goal_moment'
        if kind:
            chain=sorted({v['id']:v for v in chain}.values(),key=lambda v:v['second'])[-8:]
            phase_stats=stats(chain)[side]
            before_score={s:sum(v['type']=='shot' and v['outcome']=='goal' and v['team']==s and v['second']<chain[0]['second'] for v in events[:i+1]) for s in TEAMS}
            after_score={s:sum(v['type']=='shot' and v['outcome']=='goal' and v['team']==s for v in events[:i+1]) for s in TEAMS}
            phases.append(dict(id='phase_'+e['id'],kind=kind,label=LABELS[kind],team=side,
                               start=chain[0]['second'],end=e['second'],clock=e['clock'],
                               revision_id=revision_info(second,revision)['id'],
                               event_ids=[v['id'] for v in chain],events=chain,
                               metrics={k:phase_stats[k] for k in ['goals','shots','complete','pressures']},
                               story=dict(before_score=before_score,after_score=after_score,through_second=e['second'],terminal_type=e['type'],terminal_outcome=e['outcome']),
                               rule='Three tagged pressures within 30s in one possession' if kind=='sustained_pressure' else
                                    'Recovery followed within 15s by the attacking possession and a shot within 75s' if kind=='recovery_to_shot' else 'Goal and up to eight preceding pass/shot events in the same possession',
                               interpretation='Observed sequence; not proof of causation'))
    return phases


def phase_context(second, phase_id, revision='original', focus='neutral'):
    phase=next((p for p in detect_phases(second,revision) if p['id']==phase_id),None)
    if phase is None: raise ValueError('Phase is not available at this time and revision')
    ctx=context(second,focus,False,revision)
    ctx.update(phase=phase,evidence=phase['events'],target=phase['events'][-1],
               kind='pressure' if phase['kind']=='sustained_pressure' else 'goal' if phase['metrics']['goals'] else 'chance')
    return ctx
