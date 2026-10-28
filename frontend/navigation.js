'use strict';
let momentNavigationKey='', currentNavigationItems=[];
function navigationItems(snapshot){
  const events=(snapshot.navigation_events||[]).filter(e=>e.second<=snapshot.second);
  const items=events.map(e=>({id:e.id,second:e.second,team:e.team,player:e.player,
    kind:e.type==='shot'?(e.outcome==='disallowed'?'disallowed':'goal'):e.type==='card'?(e.outcome==='red'?(e.card_reason==='second_yellow'?'second_yellow':'red_card'):'yellow_card'):e.type==='kickoff'?'second_half':e.type,
    category:['card','offside','substitution'].includes(e.type)?'rules':'match'}));
  const goalTimes=new Set(events.filter(e=>e.type==='shot').map(e=>e.second));
  for(const p of snapshot.phases||[]){
    if(p.end<=snapshot.second&&!goalTimes.has(p.end))items.push({id:p.id,phase_id:p.id,second:p.end,team:p.team,kind:p.kind,category:'match'});
  }
  return items.sort((a,b)=>b.second-a.second||a.id.localeCompare(b.id));
}
function setupMomentNavigation(){
  Object.assign(words.en,{keyMoments:'Key moments',momentsShort:'Moments',matchNavigation:'Match navigation',demoTour:'Demo tour · spoilers',matchMoments:'Match moments',rulesChanges:'Rules & changes',navEmpty:'Key moments will appear as the match unfolds.',rulesEmpty:'No rule events or changes yet.',normalNavNote:'Only moments that have happened by the current playhead are shown.',demoNavNote:'Spoilers enabled: these shortcuts can jump ahead in the demo. Match facts still follow the playhead.',navGoal:'Goal'});
  Object.assign(words.zh,{keyMoments:'关键时刻',momentsShort:'关键时刻',navGoal:'进球',matchNavigation:'比赛导航',demoTour:'演示导览 · 含剧透',matchMoments:'比赛时刻',rulesChanges:'规则与换人',navEmpty:'关键时刻将在比赛进行中出现。',rulesEmpty:'当前尚无规则事件或换人。',normalNavNote:'只显示截至当前回放时间已发生的时刻。',demoNavNote:'已开启剧透：这些快捷入口可提前跳转，比赛数据仍依据当前时间。'});
  for(const id of ['match-moments','rule-moments'])$(id).onclick=event=>{
    const button=event.target.closest('[data-navigation-id]');if(!button)return;
    const item=currentNavigationItems.find(v=>v.id===button.dataset.navigationId);if(item)jumpToMoment(item);
  };
  document.addEventListener('pointerdown',event=>{const nav=$('moment-navigation');if(!nav.contains(event.target))nav.open=false;});
  $('moment-navigation').addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();$('moment-navigation').open=false;$('moment-navigation').querySelector('summary').focus();}});
}
function renderMomentNavigation(s){
  const items=navigationItems(s);
  const signature=JSON.stringify([language,s.revision?.id,items]);
  if(signature===momentNavigationKey)return;momentNavigationKey=signature;currentNavigationItems=items;
  $('moment-mode-note').textContent=tr('normalNavNote');
  const focused=document.activeElement?.dataset.navigationId;
  for(const [id,category] of [['match-moments','match'],['rule-moments','rules']]){
    const group=items.filter(v=>v.category===category);
    $(id).innerHTML=group.length?group.map(v=>`<button class="moment-choice" data-navigation-id="${esc(v.id)}"><b>${time(v.second)}</b><span>${esc(tr(v.kind==='pressure'?'thePress':v.kind==='goal'?'navGoal':v.kind))}${v.team?`<small>${esc(teamName(v.team))}${v.player?' · '+esc(v.player):''}</small>`:''}</span></button>`).join(''):`<p class="moment-empty">${tr(category==='match'?'navEmpty':'rulesEmpty')}</p>`;
  }
  if(focused){const button=Array.from($('moment-navigation').querySelectorAll('[data-navigation-id]')).find(v=>v.dataset.navigationId===focused);button?.focus({preventScroll:true});}
}
async function jumpToMoment(item){
  $('moment-navigation').open=false;setPlaying(false);phasePlayback=null;selectedPhaseId=null;selectedPhaseData=null;
  const target=item.second;await setTime(target,true,false);
  if(second!==target)return;
  if(item.phase_id&&latestState?.phases.some(p=>p.id===item.phase_id))choosePhase(item.phase_id);
  else generateInsight();
}
