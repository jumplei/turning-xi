"""Server-only Azure v1 Responses integration; validated evidence IDs, bounded cache."""
import json
import hashlib
import os
import threading
import time
from collections import OrderedDict, deque
from pathlib import Path
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen

from .evidence_tools import TOOLS, execute_calls, EvidenceWorkflowError
from .engine import context, template
from .phases import phase_context
from .verification import fact_catalog, validate_claims, stats_card, ClaimValidationError

CACHE = OrderedDict()
LOCK = threading.Lock()
INFLIGHT = {}
CALLS = deque()
SESSION_STARTED = time.monotonic()
SESSION_CALLS = int(os.getenv('PHASELENS_SESSION_CALLS_USED', '0'))
SESSION_LIMIT = int(os.getenv('PHASELENS_SESSION_CALL_LIMIT', '0'))
SESSION_SECONDS = int(os.getenv('PHASELENS_SESSION_SECONDS', '0'))
SESSION_STATE_FILE = os.getenv('PHASELENS_SESSION_STATE_FILE', '')
if SESSION_STATE_FILE and Path(SESSION_STATE_FILE).exists():
    saved=json.loads(Path(SESSION_STATE_FILE).read_text())
    if saved['call_limit'] != SESSION_LIMIT:
        raise RuntimeError('Stored model budget differs from configured approval')
    SESSION_CALLS=max(SESSION_CALLS,int(saved['calls_used']))


def save_session():
    if not SESSION_STATE_FILE:return
    target=Path(SESSION_STATE_FILE)
    temporary=target.with_suffix('.tmp')
    temporary.write_text(json.dumps(dict(call_limit=SESSION_LIMIT,calls_used=SESSION_CALLS)))
    temporary.chmod(0o600)
    temporary.replace(target)



def session_status():
    with LOCK:
        return dict(call_limit=SESSION_LIMIT or None, calls_used=SESSION_CALLS,
                    calls_remaining=max(0,SESSION_LIMIT-SESSION_CALLS) if SESSION_LIMIT else None,
                    seconds_remaining=max(0,int(SESSION_SECONDS-(time.monotonic()-SESSION_STARTED))) if SESSION_SECONDS else None)




def configured():
    return bool(os.getenv('AZURE_OPENAI_ENDPOINT') and
                (os.getenv('AZURE_OPENAI_API_KEY') or os.getenv('AZURE_OPENAI_AUTH_MODE') == 'managed_identity'))


@lru_cache(maxsize=1)
def managed_credential():
    from azure.identity import ManagedIdentityCredential
    return ManagedIdentityCredential()


def authentication_headers():
    if os.getenv('AZURE_OPENAI_AUTH_MODE', 'api_key') == 'managed_identity':
        try:
            token = managed_credential().get_token('https://cognitiveservices.azure.com/.default')
        except Exception as exc:
            raise RuntimeError('Managed identity authentication failed') from exc
        return {'Authorization': 'Bearer ' + token.token}
    return {'api-key': os.environ['AZURE_OPENAI_API_KEY']}


def response_url(endpoint):
    endpoint = endpoint.rstrip('/')
    parsed = urlparse(endpoint)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.fragment or parsed.username or parsed.password:
        raise ValueError('Endpoint must be an HTTPS resource or Responses endpoint')
    if parsed.path == '/openai/responses':
        params = parse_qs(parsed.query)
        if set(params) != {'api-version'} or len(params['api-version']) != 1:
            raise ValueError('Preview Responses URL requires only an api-version parameter')
        return endpoint
    if parsed.query:
        raise ValueError('Unexpected endpoint parameters')
    if parsed.path == '/openai/v1/responses':
        return endpoint
    if parsed.path == '/openai/v1':
        return endpoint + '/responses'
    if parsed.path in ('', '/'):
        return endpoint + '/openai/v1/responses'
    raise ValueError('Use a resource root or Responses endpoint, not a portal or project URL')


def model_fact_catalog(ctx, language):
    # The keys already identify facts. Omit duplicate IDs/display strings from model input.
    return {key:dict(value=fact['value'],label=fact['label'].replace('Northbridge FC','NBR').replace('Harbour Athletic','HBA').replace('last five playing minutes','recent window').replace('previous five playing minutes','previous window')) for key,fact in fact_catalog(ctx,language).items()}


def azure_response(ctx, mode, language, recap, analysis_path=None):
    timings={}
    use_tools=(analysis_path=="deep" or analysis_path is None and os.getenv("TURNING_XI_AGENTIC")=="1")
    url = response_url(os.environ['AZURE_OPENAI_ENDPOINT'])
    evidence_ids=[e['id'] for e in ctx['evidence']]
    evidence_item=dict(type='string',enum=evidence_ids) if evidence_ids else dict(type='string')
    schema = dict(type='object', additionalProperties=False, properties={
        'title': dict(type='string'), 'text': dict(type='string'),
        'evidence_ids': dict(type='array', items=evidence_item,minItems=1 if evidence_ids else 0,maxItems=len(evidence_ids)),
        'claims': dict(type='array',maxItems=6,items=dict(type='object',additionalProperties=False,properties={'fact_id':dict(type='string'),'value':dict(type='string')},required=['fact_id','value'])),
    }, required=['title', 'text', 'evidence_ids', 'claims'])
    instruction = (
        'You are Turning XI, an evidence-grounded football analyst. All data is synthetic. '
        'Use only the supplied facts. Never invent metrics, player attributes, video observations, '
        'or future events. Distinguish observations from plausible interpretations; do not assert '
        'that pressure caused an error without evidence. No markdown. Output JSON matching schema. '
        'Title <= 65 characters, text <= 110 words. Cite 1-8 supplied event IDs if events exist, '
        'otherwise use an empty list. Fan mode: accessible story, little jargon. '
        'Analyst mode: exact computed metrics, time windows, and cautious interpretation. '
        'For a recap, summarize the score and supplied goals before discussing recent play. '
        'Cite every supplied goal event ID present in the evidence. Never invent or derive event IDs. '
        'When match_status is full_time, the score is final: describe the winner or draw, '
        'not an ongoing lead or a chance still to equalise. '
        'Use display_clock for event time; second is elapsed replay time including a 15-minute half-time interval. '
        'At half_time, describe the interval rather than claiming play is continuing. '
        'Use personnel for current on-pitch counts. Cards and substitutions are state changes, '
        'A yellow immediately followed by a red marked second_yellow is ONE second-caution incident, '
        'not two new yellow cards. Use discipline history for the earlier caution time; never invent its timing. '
        'and an offside snapshot is synthetic, never video or VAR evidence. '
        'Return at most three typed claims with fact_id and the exact STRING value from fact_catalog. '
        'Title and text are qualitative prose only: NO scorelines, clocks, percentages, numerical counts, '
        'numeric literals or {{fact_id}} tokens. Figures belong ONLY in claims; the application displays '
        'the checked facts separately. Explain what happened and why it matters without repeating stats. '
        'Use player names only when present in the supplied evidence. '
        'Do not invent player names. Keep the remaining prose a cautious, number-free interpretation. '
        'Respect the selected team focus. Write in ' + ('English.' if language == 'en' else 'Simplified Chinese.')
    )
    payload = dict(model=os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-6-luna'),
                   instructions=instruction, input=json.dumps(dict(task=('full-match recap' if ctx['match_status'] == 'full_time' else 'recap so far') if recap else ('explain the full-time result and supplied goals' if ctx['match_status'] == 'full_time' else 'explain latest moment'),
                   audience=mode, context=ctx, fact_catalog=model_fact_catalog(ctx,language)), ensure_ascii=False,separators=(',',':')),
                   max_output_tokens=1200, store=False,
                   text=dict(format=dict(type='json_schema', name='match_insight', strict=True, schema=schema)))
    if not use_tools:
        payload['reasoning']=dict(effort='none' if recap else 'low')
    def send(request_payload):
        encoded = json.dumps(request_payload,ensure_ascii=False,separators=(',',':')).encode()
        if SESSION_LIMIT and len(encoded) > 16000:
            raise ValueError('Trial input exceeds the approved payload bound')
        req = Request(url, data=encoded, method='POST',
                      headers={'Content-Type': 'application/json', **authentication_headers()})
        with urlopen(req, timeout=22) as response:
            raw = json.loads(response.read(1000000))
        if raw.get('status') != 'completed':
            exc=ValueError('Model response did not complete')
            exc.diagnostic_code='model_incomplete_'+str((raw.get('incomplete_details') or {}).get('reason','unknown'))
            exc.usage={k:raw.get('usage',{}).get(k) or 0 for k in ('input_tokens','output_tokens','total_tokens')}
            raise exc
        return raw

    workflow = dict(mode='direct', status='completed', steps=[])
    planning_usage = {}
    if use_tools:
        brief = dict(task='Select evidence tools for a recap' if recap else 'Select evidence tools to explain this moment',
                     audience=mode, language=language, focus=ctx['focus'],
                     has_evidence=bool(ctx['evidence']), required_tools=(['get_event_sequence'] if ctx['evidence'] else [])+(['get_personnel_state'] if ctx['kind']=='discipline' else []), snapshot={key:ctx[key] for key in ('second','display_clock','match_status','revision','kind','target')})
        inputs = [dict(role='user', content=json.dumps(brief, ensure_ascii=False,separators=(',',':')))]
        stage_started=time.monotonic()
        planned = send(dict(model=payload['model'], store=False, max_output_tokens=700,
                            instructions='Select one to three read-only evidence tools. Call ALL required_tools from the request in this single response. '
                            'There is no second tool-selection round. For discipline, call BOTH get_event_sequence and get_personnel_state. '
                            'Inspect the event sequence when evidence exists. '
                            'Choose window comparison for rhythm or pressure and personnel state for cards or substitutions. '
                            'Do not write the narrative yet. No tools can change the snapshot.',
                            input=inputs, tools=TOOLS, tool_choice='required'))
        timings['planner_ms']=round((time.monotonic()-stage_started)*1000)
        stage_started=time.monotonic()
        tool_results, steps = execute_calls(planned.get('output', []), ctx)
        timings['tools_ms']=round((time.monotonic()-stage_started)*1000)
        # Include all output items (including reasoning items) when continuing without server storage.
        inputs += planned['output'] + tool_results
        inputs.append(dict(role='user', content=json.dumps(dict(
            task='Write the requested narrative using the inspected evidence. Missing tool data cannot support a claim.',
            audience=mode, language=language, focus=ctx['focus'],
            match_status=ctx['match_status'], display_clock=ctx['display_clock'],
            fact_catalog=model_fact_catalog(ctx,language)), ensure_ascii=False,separators=(',',':'))))
        payload['input'] = inputs
        planning_usage = planned.get('usage', {})
        workflow = dict(mode='bounded_tools', status='completed', model_requests=2, steps=steps)
    stage_started=time.monotonic()
    raw = send(payload)
    timings['writer_ms']=round((time.monotonic()-stage_started)*1000)
    stage_started=time.monotonic()
    output = ''.join(c.get('text', '') for item in raw.get('output', [])
                     for c in item.get('content', []) if c.get('type') == 'output_text')
    result = json.loads(output)
    if not isinstance(result, dict) or set(result) != {'title', 'text', 'evidence_ids', 'claims'}:
        raise ValueError('Unexpected model output')
    if not isinstance(result['title'], str) or not 1 <= len(result['title']) <= 160:
        raise ValueError('Invalid title')
    if not isinstance(result['text'], str) or not 1 <= len(result['text']) <= 1800:
        raise ValueError('Invalid narrative')
    ids = result['evidence_ids']
    allowed = {e['id'] for e in ctx['evidence']}
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids) or len(ids) > 8:
        raise ValueError('Invalid evidence references')
    # Repeated references add no evidence; keep each supplied ID once in order.
    ids=list(dict.fromkeys(ids))
    result['evidence_ids']=ids
    if set(ids) - allowed or allowed and not ids:
        raise ValueError('Unsupported evidence references')
    if recap and {e['id'] for e in ctx['evidence'] if e['outcome']=='goal'}-set(ids):
        raise ValueError('Recap omits goal evidence')
    usage={k:(raw.get('usage',{}).get(k) or 0)+(planning_usage.get(k) or 0) for k in ('input_tokens','output_tokens','total_tokens')}
    try:
        result=validate_claims(result,ctx,language)
    except ClaimValidationError as exc:
        timings['validation_ms']=round((time.monotonic()-stage_started)*1000)
        exc.timings=timings
        exc.workflow=workflow
        exc.usage=usage
        raise
    result['usage'] = {k: (raw.get('usage', {}).get(k) or 0) + (planning_usage.get(k) or 0) for k in ('input_tokens', 'output_tokens', 'total_tokens')}
    timings['validation_ms']=round((time.monotonic()-stage_started)*1000)
    result['timings']=timings
    result['workflow'] = workflow
    return result


def narrate(second, mode='fan', language='en', focus='neutral', recap=False, revision='original', phase_id=None, analysis_path=None):
    global SESSION_CALLS
    context_started=time.monotonic()
    ctx = phase_context(second,phase_id,revision,focus) if phase_id and not recap else context(second,focus,recap,revision)
    if ctx['match_status']=='full_time' and not phase_id and not recap:
        ctx=context(second,focus,True,revision)
    context_ms=round((time.monotonic()-context_started)*1000)
    use_tools=(analysis_path=='deep' or analysis_path is None and os.getenv('TURNING_XI_AGENTIC')=='1')
    # One bounded cache is shared; requests with different preferences never collide.
    key = (second, mode, language, focus, recap, ctx['revision']['id'], phase_id, os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-6-luna'),
           os.getenv('AZURE_OPENAI_AUTH_MODE', 'api_key'), 'deep' if use_tools else 'fast')
    with LOCK:
        if key in CACHE:
            CACHE.move_to_end(key)
            return dict(CACHE[key],cached=True,model_session=dict(call_limit=SESSION_LIMIT or None,calls_used=SESSION_CALLS,calls_remaining=max(0,SESSION_LIMIT-SESSION_CALLS) if SESSION_LIMIT else None))
        flight=INFLIGHT.get(key)
        leader=flight is None
        if leader:
            flight=dict(event=threading.Event())
            INFLIGHT[key]=flight
    if not leader:
        if not flight['event'].wait(55):
            raise ValueError('Equivalent insight is still running')
        if 'error' in flight:raise flight['error']
        return dict(flight['result'],coalesced=True,model_session=session_status())
    try:
        result=_generate_narrative(ctx,key,context_ms,mode,language,recap,phase_id,analysis_path,use_tools)
        flight['result']=result
        return result
    except Exception as exc:
        flight['error']=exc
        raise
    finally:
        with LOCK:
            INFLIGHT.pop(key,None)
            flight['event'].set()


def _generate_narrative(ctx,key,context_ms,mode,language,recap,phase_id,analysis_path,use_tools):
    global SESSION_CALLS
    second=ctx['second'];focus=ctx['focus']
    started=time.monotonic()
    result=template(ctx,mode,language,recap)
    source,reason='template','not_configured'
    verification=dict(status='computed_template',scope='Deterministic template; not an AI claim audit')
    allowed=False
    if configured():
        with LOCK:
            now=time.monotonic()
            while CALLS and now-CALLS[0]>=60:CALLS.popleft()
            request_budget=2 if use_tools else 1
            if SESSION_SECONDS and now-SESSION_STARTED>=SESSION_SECONDS:reason='trial_expired'
            elif SESSION_LIMIT and SESSION_CALLS+request_budget>SESSION_LIMIT:reason='trial_limit_reached'
            elif len(CALLS)+request_budget>12:reason='rate_limited'
            else:
                CALLS.extend([now]*request_budget)
                SESSION_CALLS+=request_budget
                save_session()
                allowed=True
        # Network work never holds the cache/budget lock.
        if allowed:
            try:
                result=azure_response(ctx,mode,language,recap,analysis_path)
                source,reason='foundry',None
                verification=result['verification']
            except EvidenceWorkflowError as exc:
                reason='evidence_tool_rejected'
                result['workflow']=dict(mode='bounded_tools',status='blocked',steps=exc.trace)
            except ClaimValidationError as exc:
                result=stats_card(ctx,language)
                result['workflow']=getattr(exc,'workflow',dict(mode='direct',status='completed',steps=[]))
                result['usage']=getattr(exc,'usage',{})
                result['timings']=getattr(exc,'timings',{})
                source,reason='stats','claim_validation_failed'
                verification=dict(status='blocked',issues=exc.issues,scope='Rejected model output replaced by computed facts')
            except HTTPError as exc:reason='azure_http_%s'%exc.code
            except (URLError,TimeoutError,OSError):reason='connection_failed'
            except (ValueError,KeyError,TypeError) as exc:
                reason='invalid_model_output'
                diagnostic_codes={'Unsupported evidence references':'unsupported_evidence',
                    'Recap omits goal evidence':'missing_goal_evidence',
                    'Trial input exceeds the approved payload bound':'input_bound_exceeded',
                    'Unexpected model output':'unexpected_output_shape',
                    'Invalid title':'invalid_title', 'Invalid narrative':'invalid_narrative',
                    'Invalid evidence references':'invalid_evidence_references',
                    'Duplicate evidence references':'duplicate_evidence_references'}
                result['diagnostic_code']=getattr(exc,'diagnostic_code',
                    'invalid_json' if isinstance(exc,json.JSONDecodeError) else diagnostic_codes.get(str(exc),'response_validation_failed'))
                result['usage']=getattr(exc,'usage',{})
            except RuntimeError:reason='authentication_failed'
    result.setdefault('timings',{})['context_ms']=context_ms
    result.setdefault('workflow',dict(mode='offline' if not configured() else 'direct',status='not_run',steps=[]))
    result=dict(result,verification=verification,revision=ctx['revision'],
                artifact_id='card_'+hashlib.sha256(repr(key).encode()).hexdigest()[:16],phase_id=phase_id,
                dependency_scope='match_snapshot',source=source,fallback_reason=reason,cached=False,
                second=second,display_clock=ctx['display_clock'],match_status=ctx['match_status'],audience=mode,language=language,focus=focus,
                model=os.getenv('AZURE_OPENAI_DEPLOYMENT','gpt-6-luna') if source=='foundry' else None,
                latency_ms=round((time.monotonic()-started)*1000),
                evidence=[e for e in ctx['evidence'] if e['id'] in result['evidence_ids']],
                metrics=ctx['recent_stats'],display_duration_ms=8000,synthetic=True,kind='recap' if recap else ctx['kind'],
                model_session=session_status())
    if source=='foundry' or reason=='not_configured':
        with LOCK:
            CACHE[key]=result
            while len(CACHE)>128:CACHE.popitem(last=False)
    return result
