'use strict';
const $ = id => document.getElementById(id);
const words = {
  en: {first_half:'First half',half_time:'Half time',second_half:'Second half',full_time:'Full time',addedTime:'ADDED TIME',intervalNote:'15-minute match interval, condensed to 3 seconds during replay. Teams change ends.',official:'Match official',kickoff:'Kick-off',free_kick:'Free kick',corner:'Corner',goal_kick:'Goal kick',throw_in:'Throw-in',penalty:'Penalty',foul:'Foul',goalkeeper_release:'Goalkeeper release',played:'played',whistle:'whistle',committed:'committed',out:'out of play',wide:'wide',blocked:'blocked',fouls:'Fouls',corners:'Corners',onTarget:'Shots on target',matchCentre:'Match centre',tagline:'Every turning point, explained.',synthetic:'SYNTHETIC MATCH',eyebrow:'MATCH INTELLIGENCE / DEMO 001',headline:'Every turning point, explained.',subhead:'Follow the moments. Understand the why. Make the match yours.',homeTeam:'HOME · NBR',awayTeam:'AWAY · HBA',matchView:'Match view',eventMap:'EVENT MAP',positions:'Event locations · not player tracking',matchStats:'The numbers',computed:'COMPUTED',matchTotal:'MATCH TOTAL',statsNote:'Pressure = tagged synthetic pressure events. No tracking or video inference.',insightRead:'The Turning XI read',explain:'EXPLAIN THE WHY',initialTitle:'Every moment has a story.',initialText:'Play the match or jump to a key moment to reveal the evidence behind the game.',evidence:'See the evidence',evidenceNote:'Linked events support the explanation; tactical interpretations are not proven causes.',refresh:'Refresh insight ↗',export:'Export overlay JSON ↓',pressurePulse:'Pressure pulse',fiveMinute:'5-MIN WINDOWS',pressureCount:'Pressure events',eventFeed:'On the pitch',yourMatch:'Your match. Your perspective.',preferencesDesc:'Same match intelligence. A perspective made for you.',viewingMode:'VIEWING MODE',fan:'Fan',analyst:'Analyst',followTeam:'FOLLOW A TEAM',language:'LANGUAGE',bigPicture:'THE BIG PICTURE',recapTitle:'The story so far.',recapDesc:'Turn the match into a concise recap, shaped by your perspective.',recapButton:'Generate recap ↗',about:'Built for explainable football storytelling. Fictional teams. Synthetic events. Traceable insights.',apiDocs:'Explore the API ↗',replay:'MATCH REPLAY',replayNote:'Accelerated synthetic event stream',play:'Play',pause:'Pause',jumpTo:'JUMP TO',thePress:'The press',theGoal:'The goal ↗',fullTime:'Full time',footer:'The game beyond the stats.',demoNotice:'DEMO · NOT A REAL MATCH',fanDesc:'The story, without the jargon.',analystDesc:'The patterns, metrics and context.',shots:'Shots',accuracy:'Pass accuracy',passes:'Completed passes',pressures:'Pressure events',neutral:'Neutral perspective',ready:'Ready for kick-off.',readyToExplain:'SELECT A MOMENT TO GENERATE AN INSIGHT',authentication_failed:'Model authentication failed',empty:'Ready for kick-off.',loading:'Reading the match…',modelReady:'Foundry configured · not yet verified',templateReady:'Template demo · connect Foundry for AI',failed:'Could not reach the match engine. Please retry.',wait:'Generating…',unauthorized:'Enter your demo access token in the preferences panel.',evidence_tool_rejected:'Evidence tool request rejected',not_configured:'AI not connected',trial_expired:'Foundry trial ended; showing template',trial_limit_reached:'Foundry trial call allowance used; showing template',rate_limited:'Model call limit reached',connection_failed:'Model connection failed',invalid_model_output:'Model output rejected',cached:'CACHED',events:'events',forFan:'FOR THE FAN',forAnalyst:'FOR THE ANALYST',asOf:'AS OF',template:'TEMPLATE',foundry:'FOUNDRY AI',notGenerated:'Generate an insight first.',downloaded:'Overlay JSON downloaded.',stale:'The previous request was discarded after a replay or preference change.',phase:'MATCH REPLAY',pass:'Pass',shot:'Shot',pressure:'Pressure',tackle:'Recovery',restart:'Restart',complete:'complete',incomplete:'intercepted',goal:'goal',saved:'saved',applied:'applied',won:'won'},
  zh: {first_half:'上半场',half_time:'中场休息',second_half:'下半场',full_time:'全场结束',addedTime:'补时',intervalNote:'比赛中场休息 15 分钟，回放时缩短为 3 秒，随后自动换边继续。',official:'比赛裁判',kickoff:'开球',free_kick:'任意球',corner:'角球',goal_kick:'球门球',throw_in:'界外球',penalty:'点球',foul:'犯规',goalkeeper_release:'门将出球',played:'进行',whistle:'鸣哨',committed:'犯规',out:'出界',wide:'偏出',blocked:'封堵',fouls:'犯规',corners:'角球',onTarget:'射正',matchCentre:'比赛中心',tagline:'读懂每一个比赛转折。',synthetic:'合成比赛',eyebrow:'比赛洞察 / 演示 001',headline:'看懂比分背后的比赛。',subhead:'跟随关键时刻，理解背后的原因，选择你的观赛视角。',homeTeam:'主队 · NBR',awayTeam:'客队 · HBA',matchView:'比赛视图',eventMap:'事件地图',positions:'事件位置 · 非球员追踪',matchStats:'比赛数据',computed:'代码计算',matchTotal:'全场累计',statsNote:'压迫统计来自合成事件标签，不使用追踪或视频推断。',insightRead:'Turning XI 洞察',explain:'解释为什么',initialTitle:'每个时刻，都有故事。',initialText:'播放比赛或跳到关键时刻，查看事件背后的证据。',evidence:'查看证据',evidenceNote:'关联事件用于支持解释；战术推断不代表已证明的因果关系。',refresh:'刷新洞察 ↗',export:'导出叠加图形 JSON ↓',pressurePulse:'压迫脉搏',fiveMinute:'五分钟窗口',pressureCount:'压迫事件',eventFeed:'场上事件',yourMatch:'你的比赛，你的视角。',preferencesDesc:'同一份比赛洞察，为你呈现不同的深度。',viewingMode:'观赛模式',fan:'球迷',analyst:'分析师',followTeam:'关注球队',language:'语言',bigPicture:'整体视角',recapTitle:'到目前为止的故事。',recapDesc:'根据你的偏好，把比赛整理为简明回顾。',recapButton:'生成回顾 ↗',about:'可解释的足球叙事。虚构球队、合成事件、可追溯的洞察。',apiDocs:'查看 API ↗',replay:'比赛回放',replayNote:'加速合成事件流',play:'播放',pause:'暂停',jumpTo:'跳转',thePress:'开始压迫',theGoal:'进球时刻 ↗',fullTime:'全场结束',footer:'看懂数据背后的比赛。',demoNotice:'演示 · 非真实比赛',fanDesc:'通俗易懂的比赛故事。',analystDesc:'深入查看模式、指标与上下文。',shots:'射门',accuracy:'传球成功率',passes:'成功传球',pressures:'压迫事件',neutral:'中立视角',ready:'等待开球。',readyToExplain:'选择一个时刻，生成比赛洞察',authentication_failed:'模型认证失败',empty:'等待开球。',loading:'正在解读比赛…',modelReady:'Foundry 已配置 · 尚未验证',templateReady:'模板演示 · 接入 Foundry 后启用 AI',failed:'无法连接比赛引擎，请重试。',wait:'正在生成…',unauthorized:'请在偏好面板中输入演示访问令牌。',not_configured:'尚未连接 AI',trial_expired:'Foundry 试用已结束，显示模板',trial_limit_reached:'Foundry 试用次数已用完，显示模板',rate_limited:'已达到模型调用上限',connection_failed:'模型连接失败',invalid_model_output:'模型输出未通过校验',cached:'已缓存',events:'个事件',forFan:'球迷视角',forAnalyst:'分析师视角',asOf:'截至',template:'模板解释',foundry:'FOUNDRY AI',notGenerated:'请先生成一条洞察。',downloaded:'叠加图形 JSON 已下载。',stale:'回放或偏好已改变，已丢弃旧请求。',phase:'比赛回放',pass:'传球',shot:'射门',pressure:'压迫',tackle:'抢断',restart:'重新开始',complete:'成功',incomplete:'被断',goal:'进球',saved:'扑救',applied:'施压',won:'成功'}
};
Object.assign(words.en, {
  offside:'Offside',offsides:'Offsides',penalised:'penalised',indirect_free_kick:'Indirect free kick',card:'Card',yellow:'Yellow card',red:'Red card',second_yellow:'Second caution',dissent:'Dissent',reckless_challenge:'Reckless challenge',serious_foul_play:'Serious foul play',substitution:'Substitution',replaced:'replaced',abandoned:'Match abandoned',insufficient_players:'fewer than seven players',
  rulesMoments:'Explore a rules moment',chooseMoment:'Choose a moment…',yellow_card:'Yellow card',red_card:'Sending-off',lineups:'Players & discipline',prefixOnly:'AT THIS MOMENT',onPitch:'on pitch',substitutions:'Changes',windows:'In-play windows',bench:'Available substitutes',withdrawn:'Substituted off',dismissed:'Sent off',rulesNote:'5 substitutions · 3 in-play windows · half-time changes use no window. Dismissed players cannot be replaced.',offsideSnapshot:'Offside snapshot · positions at the pass',secondLast:'Second-last opponent',scriptedStory:'Scripted demonstration',goalkeeper:'GK'
});
Object.assign(words.zh, {
  offside:'越位',offsides:'越位',penalised:'判罚',indirect_free_kick:'间接任意球',card:'出牌',yellow:'黄牌',red:'红牌',second_yellow:'两黄变一红',dissent:'异议',reckless_challenge:'鲁莽犯规',serious_foul_play:'严重犯规',substitution:'换人',replaced:'换下',abandoned:'比赛中止',insufficient_players:'场上不足七人',
  rulesMoments:'查看规则关键时刻',chooseMoment:'选择一个时刻…',yellow_card:'黄牌',red_card:'罚下',lineups:'阵容与纪律',prefixOnly:'截至当前',onPitch:'人在场',substitutions:'换人',windows:'比赛中换人窗口',bench:'可用替补',withdrawn:'已换下',dismissed:'已罚下',rulesNote:'最多换5人 · 比赛中3个换人窗口 · 中场换人不占窗口。被罚下的球员不能由替补补足。',offsideSnapshot:'越位快照 · 传球瞬间位置',secondLast:'倒数第二名对手',scriptedStory:'预设演示情节',goalkeeper:'门将'
});
let language = 'en', mode = 'fan', second = 0, playing = false, speed = 30;
let matchMeta = null, matchDuration = 0, intervalTicks = 0;
let latestState = null, latestInsight = null, health = null, epoch = 0, renderedMatchStatus = null;
let stateSequence = 0, insightBusy = false, queuedInsight = null, lastTrigger = '', recapBusy = false;
let activeInsightEpoch=null;
let preferenceTimer=null,healthReachable=true,aiDisplayState='ready',lastModelResult=null;
const tr = key => words[language][key] || key;
const elapsedTime = s => `${String(Math.floor(s / 60)).padStart(2,'0')}:${String(s % 60).padStart(2,'0')}`;
function time(s) {
  if (!matchMeta) return elapsedTime(s);
  const c=matchMeta.schedule;
  const p=s<c.second_half_start?1:2;
  const local=p===1?Math.min(s,c.half_time_start):s-c.second_half_start;
  if(local>=c.half_seconds) {const extra=local-c.half_seconds;return `${p===1?45:90}+${Math.floor(extra/60)}:${String(extra%60).padStart(2,'0')}`;}
  return elapsedTime(local+(p===2?2700:0));
}
function phaseLabel(s) {return `${tr(s.match_status)}${s.added_time?' · '+tr('addedTime'):''}`.toUpperCase();}
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const teamName = side => side === 'home' ? 'Northbridge FC' : side === 'away' ? 'Harbour Athletic' : tr('official');
function toast(text, duration=4500) { $('toast').textContent = text; $('toast').hidden = false; clearTimeout(toast.timer); toast.timer = setTimeout(() => $('toast').hidden = true, duration); }
function resetRead() { latestInsight = null;lastModelResult=null;aiDisplayState='ready';renderAIStatus(); $('insight-body').innerHTML = `<h3>${tr('initialTitle')}</h3><p>${tr('initialText')}</p>`; $('evidence-list').replaceChildren(); $('workflow-trace').hidden=true; $('workflow-trace').replaceChildren(); $('evidence-count').textContent = `0 ${tr('events')}`; $('insight-time').textContent = '—'; $('export-overlay').disabled = true; $('insight-source').className = 'source-label'; $('insight-source').textContent = health?.model_configured ? tr('readyToExplain') : `${tr('template')} · ${tr('not_configured')}`; $('recap-result').replaceChildren(); $('verification-status').replaceChildren(); inspectedEvent=null; renderBroadcastPreview(); scheduleInsightFit(); }
function translate() {
  document.documentElement.lang = language; document.body.classList.toggle('zh',language === 'zh');
  document.querySelectorAll('[data-i18n]').forEach(el => el.textContent = tr(el.dataset.i18n));
  $('focus').options[0].textContent = tr('neutral');
  $('mode-description').textContent = tr(mode === 'fan' ? 'fanDesc' : 'analystDesc');
  $('audience-label').textContent = tr(mode === 'fan' ? 'forFan' : 'forAnalyst');
  renderAIStatus();
  $('play').textContent = tr(playing ? 'pause' : 'play');
  if(latestState) $('match-phase').textContent = phaseLabel(latestState);
  if(latestState) renderMomentNavigation(latestState);
  if (latestState) renderState(latestState);
}
function eventDescription(e) {
  if(e.type==='card') return `${tr(e.card_color)} · ${tr(e.card_reason)}`;
  if(e.type==='substitution') return `${e.player} → ${e.incoming_player}`;
  return `${tr(e.type)} · ${tr(e.outcome)}`;
}
let lineupSignature = '';
function renderLineups(s) {
  const signature=JSON.stringify([language,s.lineups,s.stats.home.yellow_cards,s.stats.home.red_cards,s.stats.away.yellow_cards,s.stats.away.red_cards]);
  if(signature===lineupSignature) return;
  lineupSignature=signature;
  const player=p=>`<span class="player-chip ${p.sent_off?'dismissed-player':''}"><b>${p.number}</b> ${esc(p.name)}${p.goalkeeper?` <small>${tr('goalkeeper')}</small>`:''}${p.yellow_cards?` <span class="caution-badge" aria-label="${p.yellow_cards} ${tr('yellow')}">${p.yellow_cards} YC</span>`:''}${p.sent_off?` <span class="red-badge">RC</span>`:''}</span>`;
  // Create disclosure nodes only once: replay updates must not reset open state or focus.
  if(!$('lineups').children.length) {
    $('lineups').innerHTML=['home','away'].map(side=>`<section class="team-roster" aria-label="${teamName(side)}"><header id="${side}-roster-heading"></header><div id="${side}-active" class="player-list roster-active"></div><div class="roster-history"><h4 id="${side}-dismissed-label"></h4><div id="${side}-dismissed" class="player-list"></div></div><div class="roster-history"><h4 id="${side}-withdrawn-label"></h4><div id="${side}-withdrawn" class="player-list"></div></div><details class="bench-details" id="${side}-bench"><summary id="${side}-bench-label"></summary><div id="${side}-bench-players" class="player-list"></div></details></section>`).join('');
  }
  for(const side of ['home','away']) {
    const r=s.lineups[side];
    $(side+'-roster-heading').innerHTML=`<h3>${teamName(side)}</h3><div class="roster-summary"><b>${r.active.length} ${tr('onPitch')}</b><span class="caution-badge">${s.stats[side].yellow_cards} YC</span><span class="red-badge">${s.stats[side].red_cards} RC</span></div><p class="roster-allowance">${tr('substitutions')} ${r.substitutions}/5 · ${tr('windows')} ${r.windows}/3</p>`;
    $(side+'-active').innerHTML=r.active.map(player).join('');
    for(const [key,label] of [['dismissed','dismissed'],['withdrawn','withdrawn']]) {
      $(side+'-'+key+'-label').textContent=tr(label);
      $(side+'-'+key).innerHTML=r[key].length?r[key].map(player).join(''):`<span class="roster-empty">${language==='zh'?'无':'None'}</span>`;
    }
    $(side+'-bench-label').textContent=`${tr('bench')} (${r.bench.length})`;
    $(side+'-bench-players').innerHTML=r.bench.map(player).join('');
  }
}
function renderOffside(e) {
  const group=$('offside-line');
  if(!e || !(e.type==='offside' || e.type==='pass' && e.outcome==='offside')) {group.replaceChildren();$('pitch').setAttribute('aria-label','Synthetic football event map');return;}
  const snap=e.pass_snapshot, xs=[...snap.opponent_x].sort((a,b)=>snap.direction*(b-a));
  const line=35+xs[1]*6.3, receiver=35+snap.receiver_x*6.3;
  group.innerHTML=`<line x1="${line}" y1="30" x2="${line}" y2="410" stroke="#ffc857" stroke-width="3" stroke-dasharray="7 5"/><circle cx="${receiver}" cy="${30+snap.receiver_y*3.8}" r="9" fill="#ffbe56" stroke="#fff" stroke-width="2"/><text x="45" y="51" fill="#ffe2a3" font-size="13">${esc(tr('offsideSnapshot'))}</text>`;
  $('pitch').setAttribute('aria-label',`${tr('offsideSnapshot')}. ${tr('secondLast')}: ${xs[1]}. Receiver: ${snap.receiver_x}. Ball: ${snap.ball_x}.`);
}

function renderState(s) {
  renderMomentNavigation(s);
  $('clock').textContent = s.display_clock; $('match-phase').textContent=phaseLabel(s);
  if(s.match_status==='half_time' && renderedMatchStatus!=='half_time') toast(tr('intervalNote'),3000);
  renderedMatchStatus=s.match_status;
  $('home-direction').textContent=`NBR ${s.attacking_directions.home===1?'→':'←'}`;
  $('away-direction').textContent=`${s.attacking_directions.away===1?'→':'←'} HBA`;
   $('home-score').textContent = s.stats.home.goals; $('away-score').textContent = s.stats.away.goals;
  $('event-count').textContent = `${s.event_count} ${tr('events').toUpperCase()}`;
  $('stats').innerHTML = [['shots','shots'],['on_target','onTarget'],['accuracy','accuracy'],['complete','passes'],['pressures','pressures'],['fouls','fouls'],['corners','corners'],['offsides','offsides']].map(([key,label]) => {
    const h=s.stats.home[key], a=s.stats.away[key], total=(h||0)+(a||0), width=total ? (h||0)/total*100 : 50;
    const format=v=>v === null ? '—' : v + (key==='accuracy' ? '%' : '');
    return `<div class="stat-row"><div class="stat-label"><b>${format(h)}</b><span>${tr(label)}</span><b>${format(a)}</b></div><div class="stat-track"><span style="width:${width}%"></span><span style="width:${100-width}%"></span></div></div>`;
  }).join('');
  renderLineups(s);
  renderEnhancements(s);
  if(s.match_status==='abandoned') setPlaying(false);
  const inspected=inspectionEvent(s), feed=inspected?[inspected,...s.events.filter(e=>e.id!==inspected.id)]:s.events;
  $('event-feed').innerHTML = feed.length ? feed.map(e=>`<div class="feed-row ${inspected?.id===e.id?'inspected':''}"><span class="feed-time">${time(e.second)}</span><span class="event-icon ${e.type==='card'?e.card_color+'-event':''}">${e.type==='card'?(e.card_color==='red'?'RC':'YC'):e.type==='offside'?'⚑':e.type==='substitution'?'⇄':e.type==='shot'?'◎':e.type==='pressure'?'↗':'→'}</span><div>${esc(e.type==='substitution'?eventDescription(e):e.player || tr('official'))} · ${esc(tr(e.type))}<small>${teamName(e.team)} · ${esc(e.type==='card'?eventDescription(e):tr(e.outcome))}${e.scripted?' · '+tr('scriptedStory'):''}</small></div></div>`).join('') : `<p class="fine-print">${tr('empty')}</p>`;
  const e = inspected || s.events[0];
  renderOffside(e);
  $('active-event').textContent = e ? `${time(e.second)}  ·  ${e.player || tr('official')}  ·  ${eventDescription(e)}` : tr('ready');
  const trail = inspected?(inspected.start&&inspected.end?[inspected]:[]):s.match_status==='half_time'?[]:s.events.filter(ev=>ev.team && ev.period===s.period && ev.start && ev.end).slice(0,5).reverse();
  $('event-trail').innerHTML = trail.map((ev,i)=>`<line x1="${35+ev.start[0]*6.3}" y1="${30+ev.start[1]*3.8}" x2="${35+ev.end[0]*6.3}" y2="${30+ev.end[1]*3.8}" stroke="${ev.team==='home'?'#baff5a':'#a9b8ff'}" stroke-width="${i===trail.length-1?3:2}" opacity="${.16+i*.16}" ${ev.type==='pressure'?'stroke-dasharray="5 5"':''}/>`).join('');
  const position=trail[trail.length-1];
  if(position) {
    const x=35+position.end[0]*6.3,y=30+position.end[1]*3.8;
    $('ball-marker').innerHTML=`<circle cx="${x}" cy="${y}" r="15" fill="${position.team==='home'?'#baff5a':'#a9b8ff'}" opacity=".15"/><circle cx="${x}" cy="${y}" r="6" fill="white" stroke="#17271e" stroke-width="2"/>`;
  } else $('ball-marker').replaceChildren();
  const max=Math.max(3,...s.trend.flatMap(b=>[b.home,b.away]));
  $('pressure-chart').innerHTML=Array.from({length:Math.ceil(matchMeta.schedule.playing_duration/300)},(_,i)=>{
    const block=s.trend[i];return `<div class="chart-slot ${block?'':'future'}" title="${i*5}–${i*5+5} min of play${block?`: NBR ${block.home}, HBA ${block.away}`:''}"><span class="chart-bar lime" style="height:${block?block.home/max*100:0}%"></span><span class="chart-bar lavender" style="height:${block?block.away/max*100:0}%"></span></div>`;
  }).join('');
}
async function updateState(auto=true,manualInsight=false) {
  const seq=++stateSequence, requested=second;
  try {
    const response=await fetch(`/api/state?second=${requested}&revision=${revision}`); if(!response.ok) throw Error(); const data=await response.json();
    if(seq!==stateSequence) return;
    const previousSecond=latestState?.second??requested;
    latestState=data; renderState(data); if(latestInsight===null)showPendingFacts(insightBusy);
    const moment=autoNarrativeMoment(data,previousSecond);
    if(auto&&!phasePlayback&&requested>0&&(manualInsight||moment&&moment.id!==lastTrigger)){
      if(moment)lastTrigger=moment.id;
      if(!manualInsight&&moment&&moment.type!=='full_time'&&$('pause-for-insight').checked)setPlaying(false);
      generateInsight();
    }
  } catch { toast(tr('failed')); setPlaying(false); }
}
function setPlaying(value) { playing=value; $('play').textContent=tr(playing?'pause':'play'); }
function setTime(value, seek=false, auto=true) {
  second=Math.min(matchDuration,Math.max(0,Math.floor(value))); $('timeline').value=second;
  $('playback-time').textContent=time(second);
  if(seek) { clearPendingIntent(); if(!phasePlayback)clearPhaseSelection(false); inspectedEvent=null; intervalTicks=0; epoch++; lastTrigger=''; resetRead(); }
  if(second===matchDuration) setPlaying(false);
  return updateState(auto,seek);
}
function sourceText(data) {
  let reason=data.fallback_reason ? (words[language][data.fallback_reason] || data.fallback_reason) : '';
  const detail=language==='zh'?{unsupported_evidence:'模型引用了不可用事件',missing_goal_evidence:'回顾遗漏进球证据',input_bound_exceeded:'请求超出输入上限',model_incomplete_max_output_tokens:'模型响应达到输出上限'}:{unsupported_evidence:'Model cited unavailable events',missing_goal_evidence:'Recap omitted goal evidence',input_bound_exceeded:'Request exceeded input bound',model_incomplete_max_output_tokens:'Model reached output limit'};
  if(data.diagnostic_code&&detail[data.diagnostic_code])reason=detail[data.diagnostic_code];
  return `${tr(data.source==='foundry'?'foundry':data.source==='stats'?'stats':'template')}${reason?' · '+reason:''}${data.cached?' · '+tr('cached'):''}`;
}
async function requestNarrative(recap=false,analysisPath='fast') {
  const response=await fetch('/api/insight',{method:'POST',headers:{'Content-Type':'application/json','X-MatchMind-Token':$('access-token').value},body:JSON.stringify({second,mode,language,focus:$('focus').value,recap,revision,analysis_path:analysisPath,phase_id:recap?null:phaseContextId()})});
  if(response.status===401) throw Error(tr('unauthorized'));
  if(!response.ok) throw Error(tr('failed'));
  return response.json();
}
function renderInsight(data) {
  latestInsight=data;trackArtifact(data,'insight');renderVerification(data);
  $('insight-body').innerHTML=`<h3>${esc(data.title)}</h3><p>${esc(data.text)}</p>`;
  $('insight-time').textContent=`${tr('asOf')} ${time(data.second)}`;
  $('insight-source').textContent=sourceText(data);
  $('insight-source').className='source-label'+(data.source==='foundry'?' live':'');
  lastModelResult=data;aiDisplayState=data.cached?'cached':data.source==='foundry'?'generated':'fallback';
  if(data.model_session&&health)health.model_session=data.model_session;renderAIStatus();
  $('evidence-count').textContent=`${data.evidence.length} ${tr('events')}`;
  $('evidence-list').innerHTML=data.evidence.map(e=>`<button class="evidence-row" data-inspect-id="${e.id}"><b>${time(e.second)}</b> · ${esc(e.player)}<br>${esc(teamName(e.team))} · ${esc(eventDescription(e))}<br><code>${esc(e.id)} / ${esc(e.possession_id)}</code></button>`).join('');
  const trace=$('workflow-trace'), steps=data.workflow?.steps||[];
  trace.hidden=!steps.length;
  const toolNames=language==='zh'?{get_event_sequence:'检查事件序列',compare_recent_windows:'比较近期时段',get_personnel_state:'检查人员状态'}:{get_event_sequence:'Inspect event sequence',compare_recent_windows:'Compare recent windows',get_personnel_state:'Inspect personnel state'};
  trace.innerHTML=steps.length?`<strong>${language==='zh'?'证据工具执行记录':'Evidence tool execution'}</strong><ol>${steps.map(step=>`<li>${esc(toolNames[step.tool]||step.tool)} · ${esc(step.status)}${step.revision?' · '+esc(step.revision):''}</li>`).join('')}</ol><small>${language==='zh'?'这是工具执行记录，不是模型的内部推理。':'Tool execution record; not private model reasoning.'}</small>`:'';
  $('export-overlay').disabled=false;
  renderBroadcastPreview();
  scheduleInsightFit();
}

function showPendingFacts(waiting=true) {
  if(!latestState)return;
  const s=latestState, home=s.stats.home, away=s.stats.away;
  latestInsight=null; $('export-overlay').disabled=true;renderBroadcastPreview();
  const zh=language==='zh';
  const score=`${home.goals}–${away.goals}`;
  $('insight-body').innerHTML=`<h3>${zh?'当前比赛事实':'Match facts now'}</h3><p>${esc(`Northbridge FC ${score} Harbour Athletic`)}<br>${zh?'射门':'Shots'}: ${home.shots}–${away.shots} · ${zh?'射正':'On target'}: ${home.on_target}–${away.on_target}</p>`;
  $('insight-time').textContent=`${tr('asOf')} ${time(s.second)}`;
  $('insight-source').className='source-label';
  $('insight-source').textContent=zh?`计算事实 · ${waiting&&health?.model_configured?'AI 解读生成中':'非 AI 解读'}`:`COMPUTED FACTS · ${waiting&&health?.model_configured?'AI explanation pending':'NOT AI-GENERATED'}`;
  $('verification-status').textContent=zh?'来自当前可见比赛数据':'From the current visible match state';
  $('evidence-list').replaceChildren(); $('evidence-count').textContent=`0 ${tr('events')}`;
  $('workflow-trace').hidden=true;
  scheduleInsightFit();
}
async function generateInsight(analysisPath='fast') {
  analysisPath=analysisPath==='deep'?'deep':'fast';
  // One active request and one latest-intent slot. Never build a request backlog.
  if(insightBusy) { queuedInsight=analysisPath; showPendingFacts(); return; }
  insightBusy=true; queuedInsight=null; const version=epoch;activeInsightEpoch=version;aiDisplayState='generating';renderAIStatus();
  showPendingFacts();
  $('refresh-insight').disabled=true; $('refresh-insight').textContent=tr('wait');
  try {
    const data=await requestNarrative(false,analysisPath);
    if(insightIsFresh(data,latestState,version,epoch)) renderInsight(data);
    else if(version===epoch){aiDisplayState='stale';showPendingFacts(false);}
  }
  catch(e) {if(version===epoch){aiDisplayState='error';showPendingFacts(false);toast(e.message);}}
  finally {
    insightBusy=false;activeInsightEpoch=null; $('refresh-insight').disabled=false; $('refresh-insight').textContent=tr('refresh');
    const next=queuedInsight;queuedInsight=null;renderAIStatus();if(next)generateInsight(next);refreshHealth();
  }
}
function changePreferences() {
  clearPendingIntent();epoch++; resetRead(); translate();
  $('fan-mode').classList.toggle('selected',mode==='fan'); $('analyst-mode').classList.toggle('selected',mode==='analyst');
  $('fan-mode').setAttribute('aria-pressed',mode==='fan'); $('analyst-mode').setAttribute('aria-pressed',mode==='analyst');
  if(second>0)preferenceTimer=setTimeout(()=>{preferenceTimer=null;generateInsight();},300);
  else showPendingFacts(false);
}
$('play').onclick=()=>{if(!playing&&selectedPhaseId&&!phasePlayback)clearPhaseSelection();if(!playing)inspectedEvent=null;if(second===matchDuration) setTime(0,true);setPlaying(!playing);};
$('restart').onclick=()=>{phasePlayback=null;setPlaying(false);setTime(0,true);};
$('speed').onchange=e=>speed=Number(e.target.value);
$('timeline').addEventListener('input',e=>{phasePlayback=null;setPlaying(false);setTime(Number(e.target.value),true,false);});
$('timeline').addEventListener('change',()=>{if(second>0) generateInsight();});
$('fan-mode').onclick=()=>{if(mode!=='fan'){mode='fan';changePreferences();}};
$('analyst-mode').onclick=()=>{if(mode!=='analyst'){mode='analyst';changePreferences();}};
$('language').onchange=e=>{language=e.target.value;changePreferences();};
$('focus').onchange=changePreferences;
$('refresh-insight').onclick=()=>generateInsight('deep');
$('export-overlay').onclick=()=>{
  if(!latestInsight) return toast(tr('notGenerated'));
  const overlayId=trackArtifact(latestInsight,'overlay');
  const data=overlayPayload(latestInsight,matchMeta);
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
  const link=document.createElement('a');link.href=url;link.download=`turning-xi-overlay-${second}-${language}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast(tr('downloaded'));
};
$('generate-recap').onclick=async()=>{
  if(recapBusy) return;
  recapBusy=true;setPlaying(false);const version=epoch;aiDisplayState='generating';renderAIStatus();
  $('generate-recap').disabled=true;$('generate-recap').textContent=tr('wait');
  try {const data=await requestNarrative(true);if(version===epoch && data.second<=second && data.revision.id===latestState?.revision.id) {lastModelResult=data;aiDisplayState=data.cached?'cached':data.source==='foundry'?'generated':'fallback';if(data.model_session&&health)health.model_session=data.model_session;trackArtifact(data,'recap');$('recap-result').innerHTML=`${esc(data.text)}${data.facts?.length?`<div class="checked-facts">${data.facts.map(f=>`<span>${esc(f.display)}</span>`).join('')}</div>`:''}<span class="recap-source">${esc(sourceText(data))} · ${time(data.second)} · ${data.revision.id}</span>`;}}
  catch(e){aiDisplayState='error';toast(e.message);}
  finally{recapBusy=false;$('generate-recap').disabled=false;$('generate-recap').textContent=tr('recapButton');renderAIStatus();refreshHealth();}
};
setInterval(()=>{
  if(!playing) return;
  if(phasePlayback){
    const next=Math.min(phasePlayback.end,second+speed), finished=next===phasePlayback.end;
    if(finished){selectedPhaseId=phasePlayback.id;phasePlayback=null;setPlaying(false);setTime(next,false,false).then(()=>generateInsight('deep'));}
    else setTime(next,false,false);
    return;
  }
  const {half_time_start:boundary,second_half_start:resume}=matchMeta.schedule;
  if(second<boundary && second+speed>=boundary) {
    intervalTicks=0;setTime(boundary);
  } else if(second>=boundary && second<resume) {
    // Preserve the full match interval in the event log, but keep replay moving.
    if(++intervalTicks>=3) {intervalTicks=0;setTime(resume);}
  } else setTime(second+speed);
},1000);
async function init(){
  try{const metaResponse=await fetch('/api/match');if(!metaResponse.ok) throw Error();matchMeta=await metaResponse.json();matchDuration=matchMeta.duration;$('timeline').max=matchDuration;$('play').disabled=false;
    $('axis-half').textContent=`45+${matchMeta.schedule.first_added/60}′`;$('axis-end').textContent=`90+${matchMeta.schedule.second_added/60}′`;
    const response=await fetch('/api/health');if(!response.ok) throw Error();health=await response.json();setupEnhancements();setupMomentNavigation();setupInsightLayout();$('token-control').hidden=!health.protected;translate();resetRead();await setTime(0);setInterval(refreshHealth,15000);}
  catch{toast(tr('failed'));$('engine-status').textContent=tr('failed');}
}
init();


let insightFitFrame=0, insightLayoutObserver=null;
function scheduleInsightFit(){
  cancelAnimationFrame(insightFitFrame);
  insightFitFrame=requestAnimationFrame(fitInsightText);
}
function fitInsightText(){
  const body=$('insight-body'),card=body.closest('.insight-panel'),field=document.querySelector('.field-panel');
  const steps=[[17,29,1.75],[16.5,28,1.7],[16,27,1.7],[15.5,26,1.65],[15,25,1.65]];
  const apply=([copy,title,leading])=>{body.style.setProperty('--insight-copy-size',copy+'px');body.style.setProperty('--insight-title-size',title+'px');body.style.setProperty('--insight-copy-leading',leading);};
  apply(steps[0]);
  const chrome=card.getBoundingClientRect().height-body.getBoundingClientRect().height;
  const target=Math.max(200,field.getBoundingClientRect().height-chrome);
  for(const step of steps){apply(step);if(body.getBoundingClientRect().height<=target)break;}
  // At the readable floor, let this card grow naturally. Never hide or truncate its text.
  positionEvidencePopover();
}
function positionEvidencePopover(){
  const details=$('evidence-details');if(!details.open)return;
  const bottom=details.querySelector('summary').getBoundingClientRect().bottom;
  details.querySelector('.evidence-popover').style.maxHeight=Math.max(120,Math.min(420,innerHeight-bottom-16))+'px';
}
function setupInsightLayout(){
  const details=$('evidence-details');
  details.addEventListener('toggle',positionEvidencePopover);
  document.addEventListener('pointerdown',event=>{if(!details.contains(event.target))details.open=false;});
  details.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();details.open=false;details.querySelector('summary').focus();}});
  insightLayoutObserver=new ResizeObserver(scheduleInsightFit);
  insightLayoutObserver.observe(document.querySelector('.field-panel'));
  window.addEventListener('resize',scheduleInsightFit);
  window.addEventListener('scroll',()=>{if(details.open)positionEvidencePopover();},{passive:true});
}


function clearPendingIntent(){clearTimeout(preferenceTimer);preferenceTimer=null;queuedInsight=null;}
function renderAIStatus(){
  const node=$('engine-status');if(!node)return;
  const zh=language==='zh',session=health?.model_session;
  if(!healthReachable)node.textContent=zh?'比赛引擎连接不可用':'Match engine unavailable';
  else if(!health?.model_configured)node.textContent=tr('templateReady');
  else if(session?.calls_remaining===0||session?.call_limit&&session.calls_used>=session.call_limit)node.textContent=zh?'AI 额度已用完 · 显示计算数据':'AI allowance used · computed data';
  else if(insightBusy&&activeInsightEpoch!==epoch&&!recapBusy)node.textContent=zh?'旧请求收尾中 · 显示当前事实':'Previous request finishing · current facts shown';
  else if(insightBusy||recapBusy)node.textContent=zh?'AI 正在生成…':'AI generating…';
  else if(aiDisplayState==='stale')node.textContent=zh?'回放已前进 · 保留当前事实':'Replay moved ahead · current facts shown';
  else if(aiDisplayState==='error')node.textContent=zh?'请求失败 · 保留当前事实':'Request failed · current facts shown';
  else if((lastModelResult?.source==='template'&&lastModelResult.fallback_reason==='invalid_model_output')||(lastModelResult?.source==='stats'&&lastModelResult.fallback_reason==='claim_validation_failed'))node.textContent=zh?'Foundry 已配置 · 输出未通过校验':'Foundry configured · output rejected';
  else if(lastModelResult)node.textContent=sourceText(lastModelResult)+(lastModelResult.source==='foundry'?' · '+(lastModelResult.latency_ms/1000).toFixed(1)+'s':'');
  else node.textContent=zh?'Foundry 就绪':'Foundry ready';
  const note=$('model-session-note');
  note.title=zh?'计数为已预留的请求额度，包含失败尝试；深入分析最多占用两次，缓存不新增调用。':'Counts reserved request slots, including failed attempts; deeper analysis uses up to two, cache hits use none.';
  note.textContent=session?.call_limit?`${session.calls_used}/${session.call_limit}`:'';
  note.setAttribute('aria-label',session?.call_limit?(zh?`AI 请求额度：已使用 ${session.calls_used}，共 ${session.call_limit} 次`:`AI request allowance: ${session.calls_used} of ${session.call_limit} used`):'');
  node.title=zh?'自动解读：进球、红牌、中场与全场；其他时刻可手动分析。':'Automatic insights: goals, red cards, half-time and full-time. Analyze other moments on demand.';
}
async function refreshHealth(){
  try{const response=await fetch('/api/health');if(!response.ok)throw Error();health=await response.json();healthReachable=true;}
  catch{healthReachable=false;}renderAIStatus();
}
