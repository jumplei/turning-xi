"""Read-only tools bound to one already-built prefix/revision context."""
import json

DESCRIPTIONS = {
    'get_event_sequence': 'Inspect up to eight supplied events for the selected moment or phase. Required when the snapshot has evidence.',
    'compare_recent_windows': 'Compare the current and previous five minutes of playing time. Use for pressure, passing or rhythm claims.',
    'get_personnel_state': 'Inspect current on-pitch counts, substitutions and dismissals. Use for cards or personnel context.',
}
TOOLS = [dict(type='function', name=name, description=description, strict=True,
              parameters=dict(type='object', properties={}, required=[], additionalProperties=False))
         for name, description in DESCRIPTIONS.items()]


class EvidenceWorkflowError(ValueError):
    def __init__(self, message, trace=None):
        super().__init__(message)
        self.trace = trace or []


def execute_calls(output, ctx):
    """No caller-controlled time, revision, paths, code or network access."""
    calls = [item for item in output if item.get('type') == 'function_call']
    if not 1 <= len(calls) <= 3:
        raise EvidenceWorkflowError('Expected one to three evidence tool calls')
    seen_names, seen_ids, results, trace = set(), set(), [], []
    for call in calls:
        name, call_id = call.get('name'), call.get('call_id')
        try:
            if name not in DESCRIPTIONS or name in seen_names:
                raise ValueError('Unknown or repeated tool')
            if not isinstance(call_id, str) or not call_id or len(call_id) > 120 or call_id in seen_ids:
                raise ValueError('Invalid tool call identity')
            arguments = json.loads(call.get('arguments', ''))
            if arguments != {}:
                raise ValueError('Tool arguments must be empty; snapshot is server-bound')
            seen_names.add(name); seen_ids.add(call_id)
            if name == 'get_event_sequence':
                if any(e['second'] > ctx['second'] for e in ctx['evidence']):
                    raise ValueError('Evidence exceeds snapshot')
                data = dict(events=ctx['evidence'], phase=ctx.get('phase'), observation_only=True)
            elif name == 'compare_recent_windows':
                data = dict(current=ctx['recent_stats'], previous=ctx['previous_stats'],
                            window_seconds=ctx['window_seconds'], basis=ctx['window_basis'])
            else:
                data = dict(personnel=ctx['personnel'], discipline_events=ctx.get('discipline_events', []),
                            note='A yellow immediately followed by a second_yellow red is one second-caution incident, not two new yellows.')
            data.update(through_second=ctx['second'], revision=ctx['revision']['id'])
        except (ValueError, TypeError, KeyError) as exc:
            raise EvidenceWorkflowError('Evidence tool request rejected', trace + [dict(tool=name, status='blocked')]) from exc
        results.append(dict(type='function_call_output', call_id=call_id, output=json.dumps(data, ensure_ascii=False)))
        trace.append(dict(tool=name, status='completed', through_second=ctx['second'], revision=ctx['revision']['id']))
    if ctx['evidence'] and 'get_event_sequence' not in seen_names:
        raise EvidenceWorkflowError('Event evidence must be inspected before writing', trace)
    if ctx['kind']=='discipline' and 'get_personnel_state' not in seen_names:
        raise EvidenceWorkflowError('Discipline explanations require personnel inspection',trace)
    return results, trace
