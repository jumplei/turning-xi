"""Pure, per-request revision views. The source event log is never mutated."""
from .match_clock import DEMO_GOAL

REVISIONS = ('original', 'goal_removed')


def revision_info(second, revision='original'):
    if revision not in REVISIONS:
        raise ValueError('Unknown revision')
    applied = revision == 'goal_removed' and second >= DEMO_GOAL
    return dict(id='r2' if applied else 'r1', scenario=revision, corrected=applied,
                effective_second=DEMO_GOAL if applied else None)


def view_events(events, second, revision='original'):
    info=revision_info(second,revision)
    return [dict(e,outcome='disallowed',original_outcome='goal',revision_id='r2',
                 correction_reason='Synthetic operator correction: invalid goal entry')
            if info['corrected'] and e['second']==DEMO_GOAL and e['outcome']=='goal' else e
            for e in events if e['second']<=second]
