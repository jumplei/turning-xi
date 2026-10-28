"""Typed fact checks and constrained fact rendering, not general semantic verification."""
import re
from .engine import PLAYERS, TEAMS

TOKEN=re.compile(r'\{\{([a-zA-Z0-9_.]+)\}\}')


class ClaimValidationError(ValueError):
    def __init__(self,issues):
        self.issues=issues
        super().__init__('; '.join(issues))


def fact_catalog(ctx,language='en'):
    zh=language=='zh'; facts={}
    def add(key,value,label):
        facts[key]=dict(fact_id=key,value=str(value),label=label,display=label+': '+str(value))
    add('match.score','%s–%s'%(ctx['stats']['home']['goals'],ctx['stats']['away']['goals']),'比分' if zh else 'Score (NBR–HBA)')
    for side in TEAMS:
        name=TEAMS[side]['name']
        for metric,en,cn in [('goals','Goals','进球'),('shots','Shots','射门'),('on_target','Shots on target','射正'),('red_cards','Red cards','红牌')]:
            add(side+'.'+metric,ctx['stats'][side][metric],name+' · '+(cn if zh else en))
        add(side+'.on_pitch',ctx['personnel'][side]['on_pitch'],name+' · '+('场上人数' if zh else 'Players on pitch'))
        for window,source,en_window,cn_window in [('recent','recent_stats','last five playing minutes','最近五分钟比赛时间'),('previous','previous_stats','previous five playing minutes','此前五分钟比赛时间')]:
            for metric,en,cn in [('passes','Pass attempts','传球次数'),('complete','Completed passes','成功传球'),('accuracy','Pass accuracy (%)','传球成功率（%）'),('pressures','Pressure events','压迫事件'),('shots','Shots','射门')]:
                add(side+'.'+window+'.'+metric,ctx[source][side][metric],name+' · '+(cn_window+' · '+cn if zh else en_window+' · '+en))

    for e in ctx['evidence']:
        if e['player_id']:
            key='player.'+e['player_id']
            facts[key]=dict(fact_id=key,value=e['player_id'],label='球员' if zh else 'Player',display=e['player'])
        add(e['id']+'.clock',e['clock'],'时间' if zh else 'Event clock')
    return facts


def validate_claims(result,ctx,language='en'):
    catalog=fact_catalog(ctx,language); issues=[]; checked=[]; ids=set()
    claims=result.get('claims')
    if not isinstance(claims,list) or len(claims)>6:
        raise ClaimValidationError(['claims_must_be_a_list_of_at_most_six'])
    for claim in claims:
        if not isinstance(claim,dict) or set(claim)!={'fact_id','value'}:
            issues.append('invalid_claim_shape');continue
        key,value=claim['fact_id'],claim['value']
        if not isinstance(key,str) or key not in catalog:
            issues.append('unknown_or_unavailable_fact');continue
        if key in ids: issues.append('duplicate_fact')
        ids.add(key)
        if not isinstance(value,str) or value!=catalog[key]['value']:
            issues.append('value_mismatch:'+key)
        else: checked.append(catalog[key])
    prose=result['title']+' '+result['text']
    tokens=TOKEN.findall(prose)
    if any(key not in ids or key not in catalog for key in tokens): issues.append('unverified_fact_token')
    remainder=TOKEN.sub('',prose)
    if re.search(r'\d',remainder): issues.append('unstructured_number_in_prose')
    available={v['display'] for k,v in catalog.items() if k.startswith('player.')}
    roster_names={name for names in PLAYERS.values() for name in names}
    mentioned=set(re.findall(r'\b[A-Z]\.\s+[A-Z][a-z]+',remainder))
    for name in mentioned | {n for n in roster_names if n in remainder}:
        if name not in available: issues.append('unsupported_player:'+name)
    if issues: raise ClaimValidationError(issues)
    rendered=dict(result)
    for key in ['title','text']:
        original=result[key]
        def render_token(match):
            fact=catalog[match.group(1)]
            start=original.rfind('\n',0,match.start())+1
            end=original.find('\n',match.end())
            line=original[start:end if end>=0 else len(original)]
            standalone=bool(re.fullmatch(r'\s*'+re.escape(match.group(0))+r'\s*[.!。]?\s*',line))
            if not standalone and not fact['fact_id'].startswith('player.'):
                return fact['value']
            return fact['display']
        rendered[key]=TOKEN.sub(render_token,original)
    # Catch the token+literal name duplication observed in the first live phase sample.
    for name in available:
        if re.search(re.escape(name)+r"(?:[’']s)?\s+"+re.escape(name),rendered['title']+' '+rendered['text']):
            raise ClaimValidationError(['repeated_player_name'])
    if not any(f['fact_id']=='match.score' for f in checked):checked.append(catalog['match.score'])
    rendered['facts']=checked
    rendered['verification']=dict(status='passed',checks=['typed_values','fact_tokens','numeric_literal_guard','roster_style_player_mentions'],
                                  scope='Typed facts and supported references; tactical prose is not proven')
    return rendered


def stats_card(ctx,language='en'):
    catalog=fact_catalog(ctx,language)
    chosen=[catalog[k] for k in ['match.score','home.shots','away.shots','home.on_pitch','away.on_pitch']]
    return dict(title='已核对的比赛数据' if language=='zh' else 'Checked match facts',
                text=('仅显示代码计算的数据。' if language=='zh' else 'Computed data only. ')+'. '.join(f['display'] for f in chosen),
                evidence_ids=[e['id'] for e in ctx['evidence']],facts=chosen)
