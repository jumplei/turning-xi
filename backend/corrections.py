"""Stateless correction preview and explicit withdrawal operations for supplied artifacts."""
from .engine import EVENTS, state, context
from .match_clock import DEMO_GOAL
from .phases import detect_phases
from .verification import validate_claims, ClaimValidationError, stats_card


def correction_preview(second, artifacts=(), language='en'):
    if second<DEMO_GOAL: raise ValueError('The goal is not visible yet')
    old=state(second); new=state(second,'goal_removed')
    goal=next(e for e in EVENTS if e['second']==DEMO_GOAL and e['outcome']=='goal')
    before=detect_phases(second);after=detect_phases(second,'goal_removed')
    withdrawn_phases=[p['id'] for p in before if p['id'] not in {v['id'] for v in after}]
    affected=[a for a in artifacts if a['revision_id']=='r1' and a['second']>=DEMO_GOAL]
    operations=[dict(operation='withdraw',artifact_id=a['id'],kind=a['kind'],reason='Depends on superseded match snapshot r1') for a in affected]
    operations += [dict(operation='withdraw',artifact_id=p,kind='phase',reason='Goal event is no longer valid') for p in withdrawn_phases]
    operations += [dict(operation='replace',artifact_id='scoreboard',kind='score',revision_id='r2')]
    ctx=context(second,revision='goal_removed')
    replacement=dict(stats_card(ctx,language),source='stats',fallback_reason='revision_corrected',
                     verification=dict(status='computed_correction'),revision=new['revision'],
                     artifact_id='correction_r2_'+str(second),second=second,display_clock=ctx['display_clock'],
                     audience='fan',language=language,focus='neutral',evidence=ctx['evidence'],metrics=ctx['recent_stats'],
                     kind='correction',synthetic=True,display_duration_ms=8000)
    return dict(synthetic=True,through_second=second,scenario='goal_removed',from_revision='r1',to_revision='r2',
                effective_second=DEMO_GOAL,target_event_id=goal['id'],
                reason='Synthetic operator correction of an invalid goal entry; no VAR/video inference',
                before={side:{k:old['stats'][side][k] for k in ['goals','shots','on_target']} for side in ['home','away']},
                after={side:{k:new['stats'][side][k] for k in ['goals','shots','on_target']} for side in ['home','away']},
                operations=operations,withdrawn_phase_ids=withdrawn_phases,
                retained_artifacts=[a for a in artifacts if a not in affected],
                replacement=replacement,
                note='Original log and later historical events are retained; this is a data correction, not an alternative simulated match. Downloaded files cannot be recalled; apply these withdrawal operations downstream.')


def verification_demo(second,revision='original',language='en'):
    ctx=context(second,revision=revision)
    candidate=dict(title='Injected test card',text='An intentionally invalid claim.',
                   evidence_ids=[e['id'] for e in ctx['evidence']],
                   claims=[dict(fact_id='home.shots',value=str(ctx['stats']['home']['shots']+7)),
                           dict(fact_id='player.H99',value='H99')])
    try: validate_claims(candidate,ctx,language)
    except ClaimValidationError as exc:
        return dict(synthetic=True,injected=True,model_called=False,status='blocked',issues=exc.issues,
                    candidate=candidate,replacement=stats_card(ctx,language),revision=ctx['revision'])
    raise AssertionError('Injected bad claim was not blocked')
