'use strict';
let revision='original', selectedPhaseId=null, selectedPhaseData=null, inspectedEvent=null;
let phasePlayback=null, phaseRenderKey='', correctionAudit=null, revisionBusy=false, claimTestRevision=null;
const displayedArtifacts=new Map();
let lastPreviewPayload=null,withdrawnOverlayId=null,broadcastRenderKey='';
function setupEnhancements(){
  Object.assign(words.en,{testSuperseded:'The previous test used a superseded snapshot. Run it again to check the current record.',allPhases:'All completed phases',turningPoints:'Turning points',observedSequences:'OBSERVED SEQUENCES',phaseIntro:'Select a completed phase, inspect its steps, or replay the sequence. Events show order, not proven causation.',noPhases:'Play the match to discover completed phases.',replayPhase:'▶ Replay this phase',phasePlaying:'Replaying this phase…',inspectHint:'Select a step to inspect its location without moving match time.',goal_build_up:'Goal build-up',recovery_to_shot:'Recovery to shot',sustained_pressure:'Sustained pressure',goal_moment:'Goal moment',trustDesk:'Match record & withdrawals',claimCheck:'Check a bad claim',claimDemoNote:'Inject an incorrect shot count and an unavailable player reference. This is an offline test, not a model response.',testClaim:'Run verification test',correctionDemo:'Correct the match record',correctionNote:'Withdraw the demo goal at 60:30. Recompute facts and remove stories that depend on the old snapshot. Synthetic operator correction, not VAR.',withdrawGoal:'Withdraw demo goal',resetCorrection:'Reset correction demo',exportPatch:'Export correction patch ↓',stats:'COMPUTED FACTS',claim_validation_failed:'Model claims blocked · data-only replacement',revision_corrected:'Corrected snapshot',computed_template:'Computed template · no AI call',passed:'Typed facts checked',blocked:'Blocked · data-only replacement',computed_correction:'Recomputed after correction',disallowed:'goal entry withdrawn',originalRevision:'Original',correctedRevision:'Corrected',withdrawnStory:'Recap cleared. Generate a recap using the corrected match record.',blockedTest:'Injected claims blocked',testReplacement:'Data-only replacement',correctionApplied:'Goal withdrawn. Score, phases and story dependencies updated.',withdrawOperation:'Withdraw',replaceOperation:'Replace',noArtifacts:'No displayed stories or exported overlays required withdrawal.',exportNote:'Previously downloaded files cannot be recalled. Use the correction patch to withdraw them downstream.',phaseOf:'Phase',latestPhases:'Latest completed phases',inspectEvent:'Inspect event'});
  Object.assign(words.zh,{testSuperseded:'上次测试使用的版本已失效，请重新核验当前记录。',allPhases:'所有完整回合',turningPoints:'比赛转折',observedSequences:'可观察的事件链',phaseIntro:'选择完整回合，查看事件步骤或回放。先后顺序不代表已证明的因果关系。',noPhases:'播放比赛，发现已完成的回合。',replayPhase:'▶ 回放这个回合',phasePlaying:'正在回放这个回合…',inspectHint:'点击步骤查看位置，不会改变比赛时间。',goal_build_up:'进球过程',recovery_to_shot:'夺回球权后射门',sustained_pressure:'持续压迫',goal_moment:'进球时刻',trustDesk:'比赛记录与内容撤回',claimCheck:'检查错误声明',claimDemoNote:'注入错误射门数和不可用球员引用。这是离线测试，并非模型响应。',testClaim:'运行核验测试',correctionDemo:'更正比赛记录',correctionNote:'撤销 60:30 的演示进球，重新计算数据并撤下依赖旧版本的故事。这是合成数据更正，非 VAR 判罚。',withdrawGoal:'撤销演示进球',resetCorrection:'重置更正演示',exportPatch:'导出更正操作 ↓',stats:'代码计算的数据',claim_validation_failed:'模型声明被阻止，已替换为数据卡',revision_corrected:'已更正版本',computed_template:'代码模板 · 未调用 AI',passed:'结构化事实已核对',blocked:'已阻止 · 显示数据替代卡',computed_correction:'已依据更正重新计算',disallowed:'进球记录已撤销',originalRevision:'原始',correctedRevision:'已更正',withdrawnStory:'回顾区域已清空，请依据更正后的比赛生成新回顾。',blockedTest:'注入的错误声明已阻止',testReplacement:'纯数据替代卡',correctionApplied:'进球已撤销，比分、回合和故事依赖已更新。',withdrawOperation:'撤下',replaceOperation:'替换',noArtifacts:'没有已显示故事或已导出叠加图形需要撤下。',exportNote:'无法收回已下载文件，请在下游应用更正操作。',phaseOf:'回合',latestPhases:'最近的完整回合',inspectEvent:'查看事件'});
  Object.assign(words.en,{pauseForAI:'Pause for AI at key moments',productionDesk:'Broadcast desk',developerCheck:'Developer validation test',simulatedInput:'SIMULATED INPUT',productionPurpose:'CORRECTIONS · WITHDRAWALS · BROADCAST OUTPUT',broadcastPreview:'Broadcast preview',sameOverlay:'SAME CONTENT AS JSON EXPORT',broadcastNote:'A graphics preview from the current overlay payload. No video or tracking feed.',graphicsCanvas:'GRAPHICS PREVIEW · SYNTHETIC MATCH',previewEmpty:'Generate an insight to preview its broadcast card.'});
  Object.assign(words.zh,{pauseForAI:'关键时刻暂停，等待 AI 解读',productionDesk:'导播专区',developerCheck:'开发者校验测试',simulatedInput:'人工构造的测试输入',productionPurpose:'更正 · 内容撤回 · 广播输出',broadcastPreview:'广播叠加卡预览',sameOverlay:'与导出 JSON 内容一致',broadcastNote:'使用当前叠加卡数据的图形预览，没有视频或跟踪信号。',graphicsCanvas:'图形预览 · 合成比赛',previewEmpty:'生成解读后即可预览广播叠加卡。'});
  $('production-desk').addEventListener('toggle',()=>{if($('production-desk').open)renderBroadcastPreview();});
  $('phase-cards').onclick=event=>{
    const card=event.target.closest('[data-phase-id]'); if(!card) return;
    choosePhase(card.dataset.phaseId);
  };
  $('phase-picker').onchange=event=>choosePhase(event.target.value);
  $('phase-inspector').onclick=event=>{
    if(event.target.closest('#back-to-match')){clearPhaseSelection();return;}
    if(event.target.closest('#replay-phase')){
      if(!selectedPhaseData)return;
      phasePlayback={...selectedPhaseData};inspectedEvent=null;speed=10;$('speed').value='10';
      setTime(phasePlayback.start,true,false);setPlaying(true);return;
    }
    const step=event.target.closest('[data-inspect-id]');if(step)inspectEventById(step.dataset.inspectId);
  };
  $('evidence-list').onclick=event=>{const row=event.target.closest('[data-inspect-id]');if(row)inspectEventById(row.dataset.inspectId);};
  $('test-claim').onclick=runVerificationTest;
  $('correct-goal').onclick=applyCorrection;
  $('export-correction').onclick=()=>{if(correctionAudit)downloadJSON(correctionAudit,`turning-xi-correction-${second}.json`);};
}
function choosePhase(id){
  if(!id){clearPhaseSelection();return;}
  const phase=latestState?.phases.find(p=>p.id===id);if(!phase)return;
  clearPendingIntent();
  setPlaying(false);phasePlayback=null;selectedPhaseId=phase.id;selectedPhaseData=phase;inspectedEvent=null;epoch++;resetRead();renderState(latestState);generateInsight('deep');
}
function phaseContextId(){return latestState?.phases.some(p=>p.id===selectedPhaseId)?selectedPhaseId:null;}
function inspectionEvent(s){return inspectedEvent && inspectedEvent.second<=s.second?inspectedEvent:null;}
function inspectEventById(id){
  const event=[...(selectedPhaseData?.events||[]),...(latestInsight?.evidence||[])].find(e=>e.id===id&&e.second<=second);
  if(!event)return;setPlaying(false);inspectedEvent=event;renderState(latestState);
}
function trackArtifact(data,kind){
  if(!data.artifact_id || !data.revision)return;
  const id=kind==='overlay'?'overlay_'+data.artifact_id:data.artifact_id;
  displayedArtifacts.set(id,{id,kind,second:data.second,revision_id:data.revision.id});
  while(displayedArtifacts.size>50)displayedArtifacts.delete(displayedArtifacts.keys().next().value);
  return id;
}
function renderEnhancements(s){
  if(claimTestRevision&&claimTestRevision!==s.revision.id){$('claim-result').textContent=tr('testSuperseded');claimTestRevision=null;}
  const phases=s.phases||[];
  const current=phases.find(p=>p.id===selectedPhaseId);
  if(current)selectedPhaseData=current;
  else if(selectedPhaseId&&!phasePlayback){selectedPhaseId=null;selectedPhaseData=null;inspectedEvent=null;}
  if(inspectedEvent && inspectedEvent.second>s.second)inspectedEvent=null;
  let shown=phases.slice(-3);
  if(current&&!shown.some(p=>p.id===current.id))shown=[current,...shown.slice(-2)];
  const visibleSteps=(selectedPhaseData?.events||[]).filter(e=>e.second<=s.second);
  const key=JSON.stringify([language,shown.map(p=>p.id),selectedPhaseId,visibleSteps.map(e=>e.id),inspectedEvent?.id,!!phasePlayback,s.revision.id]);
  if(key!==phaseRenderKey){
    phaseRenderKey=key;
    $('phase-picker').innerHTML=`<option value="">${tr('allPhases')} (${phases.length})</option>`+[...phases].reverse().map(p=>`<option value="${p.id}">${time(p.end)} · ${teamName(p.team)} · ${tr(p.kind)}</option>`).join('');
    $('phase-picker').value=current?.id||'';
    $('phase-cards').innerHTML=shown.length?shown.map(p=>`<button class="phase-card ${p.id===selectedPhaseId?'selected':''}" data-phase-id="${p.id}" aria-pressed="${p.id===selectedPhaseId}"><span>${time(p.start)}–${time(p.end)} · ${teamName(p.team)}</span><strong>${tr(p.kind)}</strong><small>${p.metrics.complete} ${tr('passes')} · ${p.metrics.pressures} ${tr('pressures')} · ${p.metrics.shots} ${tr(p.metrics.shots===1?'shot':'shots')}</small></button>`).join(''):`<p class="fine-print">${tr('noPhases')}</p>`;
    $('phase-inspector').innerHTML=selectedPhaseData?`<div class="phase-inspector-heading"><strong>${tr(selectedPhaseData.kind)} · ${time(selectedPhaseData.start)}–${time(selectedPhaseData.end)}</strong><div class="phase-actions"><button id="back-to-match" class="button button-ghost">${language==='zh'?'返回当前比赛':'Back to match'}</button><button id="replay-phase" class="button button-dark" ${phasePlayback?'disabled':''}>${tr(phasePlayback?'phasePlaying':'replayPhase')}</button></div></div>${phaseStoryHtml(selectedPhaseData,s)}<p class="fine-print">${tr('inspectHint')}</p><div class="phase-steps">${visibleSteps.map((e,i)=>`<button class="phase-step ${inspectedEvent?.id===e.id?'selected':''}" data-inspect-id="${e.id}"><b>${i+1} · ${time(e.second)}</b><span>${esc(e.player)} · ${esc(eventDescription(e))}</span><code>${e.id}</code></button>`).join('')}</div>`:'';
  }
  $('revision-label').textContent=`${s.revision.id} · ${tr(s.revision.corrected?'correctedRevision':'originalRevision')}`;
  $('correct-goal').disabled=revisionBusy || revision==='original' && second<matchMeta.key_moments.find(m=>m.key==='goal').second;
  $('correct-goal').textContent=tr(revision==='original'?'withdrawGoal':'resetCorrection');
  renderCorrectionAudit();
  renderBroadcastPreview();
  const selected=inspectionEvent(s);
  $('inspection-marker').innerHTML=selected?.end?`<circle cx="${35+selected.end[0]*6.3}" cy="${30+selected.end[1]*3.8}" r="13" fill="none" stroke="#ffd15e" stroke-width="3"/><text x="45" y="395" fill="#ffe2a3" font-size="13">${esc(tr('inspectEvent'))}: ${selected.id} · ${time(selected.second)}</text>`:'';
}
function renderVerification(data){
  $('verification-status').className='verification-status '+(data.verification?.status==='blocked'?'verification-blocked':'');
  $('verification-status').textContent=`${data.revision?.id||''} · ${tr(data.verification?.status||'computed_template')}`;
  const extraFacts=(data.facts||[]).filter(f=>!data.text.includes(f.display)&&!data.title.includes(f.display));
  if(extraFacts.length)$('verification-status').innerHTML+=`<div class="checked-facts">${extraFacts.map(f=>`<span>${esc(f.display)}</span>`).join('')}</div>`;
}
function downloadJSON(data,name){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function runVerificationTest(){
  $('test-claim').disabled=true;const version=epoch,testedSecond=second;
  try{
    const response=await fetch('/api/verification/demo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({second,revision,language})});
    if(!response.ok)throw Error(tr('failed'));const data=await response.json();
    if(version!==epoch)return;claimTestRevision=data.revision.id;
    $('claim-result').innerHTML=`<strong class="blocked-label">${tr('blockedTest')}</strong><p>${data.revision.id} · ${tr('asOf')} ${time(testedSecond)}</p><p>${language==='zh'?'注入的声明':'Injected claim'}: ${esc(data.candidate.claims[0].fact_id)} = ${esc(data.candidate.claims[0].value)}; ${esc(data.candidate.claims[1].fact_id)}</p><ul>${data.issues.map(i=>`<li><code>${esc(i)}</code></li>`).join('')}</ul><strong>${tr('testReplacement')}</strong><p>${esc(data.replacement.text)}</p>`;
  }catch(e){toast(e.message);}finally{$('test-claim').disabled=false;}
}
async function applyCorrection(){
  if(revisionBusy)return;clearPendingIntent();revisionBusy=true;setPlaying(false);phasePlayback=null;epoch++;inspectedEvent=null;
  const version=epoch, requestedSecond=second;
  $('correct-goal').disabled=true;
  try{
    if(revision==='goal_removed'){
      revision='original';correctionAudit=null;withdrawnOverlayId=null;lastPreviewPayload=null;displayedArtifacts.clear();claimTestRevision=null;$('claim-result').replaceChildren();$('correction-result').replaceChildren();$('export-correction').disabled=true;
      selectedPhaseId=null;selectedPhaseData=null;resetRead();await updateState(false);return;
    }
    const response=await fetch('/api/corrections/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({second,language,artifacts:[...displayedArtifacts.values()]})});
    if(!response.ok)throw Error(tr('failed'));const audit=await response.json();
    if(version!==epoch||requestedSecond!==second){toast(tr('stale'));return;}
    correctionAudit=audit;
    if(lastPreviewPayload&&audit.operations.some(o=>o.operation==='withdraw'&&o.artifact_id===lastPreviewPayload.artifact_id))withdrawnOverlayId=lastPreviewPayload.artifact_id;
    revision='goal_removed';selectedPhaseId=null;selectedPhaseData=null;resetRead();await updateState(false);
    if(version!==epoch||requestedSecond!==second){toast(tr('stale'));return;}
    renderInsight(correctionAudit.replacement);
    $('recap-result').textContent=tr('withdrawnStory');
    renderCorrectionAudit();
    $('export-correction').disabled=false;
  }catch(e){toast(e.message);}finally{revisionBusy=false;if(latestState)renderEnhancements(latestState);}
}

function phaseStoryHtml(phase,snapshot){
  if(!phase.story||phase.end>snapshot.second)return '';
  const zh=language==='zh',story=phase.story,m=phase.metrics;
  const score=value=>`${value.home}–${value.away}`;
  const outcome=story.terminal_outcome==='goal'?(zh?'进球，比分改变':'Goal changes the score'):(zh?'比分保持不变':'Score unchanged');
  return `<div class="phase-story"><div><span>${zh?'之前':'BEFORE'} · ${time(phase.start)}</span><strong>${score(story.before_score)}</strong><small>${zh?'回合开始前的比分':'Score before the sequence'}</small></div><div><span>${zh?'过程':'OBSERVED SEQUENCE'}</span><strong>${m.complete} ${zh?'次成功传球':'completed passes'}</strong><small>${m.pressures} ${zh?'次压迫':'pressure events'} · ${m.shots} ${zh?'次射门':m.shots===1?'shot':'shots'}</small></div><div><span>${zh?'结果':'AT THE END'} · ${time(phase.end)}</span><strong>${score(story.after_score)}</strong><small>${outcome}</small></div></div><p class="phase-observation">${zh?'代码识别的事件顺序，不代表已证明的因果关系。':'Computed event sequence; timing alone does not prove causation.'}</p>`;
}
function renderBroadcastPreview(){
  const card=$('overlay-card');if(!card)return;
  const data=matchMeta?overlayPayload(latestInsight,matchMeta):null;
  const zh=language==='zh';
  if(data&&$('production-desk').open){lastPreviewPayload=data;trackArtifact(latestInsight,'overlay');}
  const key=JSON.stringify([data?.artifact_id,data?.title,data?.text,data?.source,data?.cached,language,withdrawnOverlayId,$('production-desk').open]);
  if(key===broadcastRenderKey)return;broadcastRenderKey=key;
  $('overlay-withdrawal').textContent=withdrawnOverlayId?(zh?'旧版 r1 叠加卡已撤回；下方内容来自当前版本。':'Previous r1 overlay withdrawn. The card below uses the current record.'):'';
  $('overlay-withdrawal').hidden=!withdrawnOverlayId;
  if(!data){card.innerHTML=`<p>${tr('previewEmpty')}</p>`;$('overlay-metadata').replaceChildren();return;}
  card.innerHTML=`<div class="overlay-card-kicker">TURNING XI · ${time(data.second)} · ${esc(data.revision.id)}</div><h3>${esc(data.title)}</h3><p>${esc(data.text)}</p>${data.facts?.length?`<div class="checked-facts">${data.facts.map(f=>`<span>${esc(f.display)}</span>`).join('')}</div>`:''}<div class="overlay-card-source">${esc(sourceText(data))}</div>`;
  $('overlay-metadata').innerHTML=`<span>${zh?'比赛时间':'MATCH TIME'} <b>${time(data.second)}</b></span><span>${zh?'建议显示时长':'SUGGESTED DURATION'} <b>${data.display_duration_ms/1000}s</b></span><span>${zh?'证据':'EVIDENCE'} <b>${data.evidence?.length||0}</b></span><span>${zh?'版本':'REVISION'} <b>${esc(data.revision.id)}</b></span><p>${zh?'静态图形预览；建议时长来自导出数据，未连接直播发布系统。':'Static graphics preview. Suggested duration comes from the export; no live publishing system is connected.'}</p>`;
}
function renderCorrectionAudit(){
  if(!correctionAudit)return;
  const a=correctionAudit,c=correctionCounts(a),zh=language==='zh';
  const score=v=>`${v.home.goals}–${v.away.goals}`;
  $('correction-result').innerHTML=`<strong>${tr('correctionApplied')}</strong><p>${tr('asOf')} ${time(a.through_second)} · r1 → r2</p><div class="correction-facts"><div><small>${zh?'比分':'SCORE'}</small><b>${score(a.before)} → ${score(a.after)}</b></div><div><small>${zh?'主队射门':'HOME SHOTS'}</small><b>${a.before.home.shots} → ${a.after.home.shots}</b></div><div><small>${zh?'主队射正':'HOME ON TARGET'}</small><b>${a.before.home.on_target} → ${a.after.home.on_target}</b></div></div><p class="withdrawal-counts">${zh?'已撤下':'Withdrawn'}: ${zh?'解读':'Insights'} <b>${c.insight}</b> · ${zh?'回顾':'Recaps'} <b>${c.recap}</b> · ${zh?'叠加卡':'Overlays'} <b>${c.overlay}</b> · ${zh?'回合':'Phases'} <b>${c.phase}</b></p><p>${c.retained} ${zh?'个此前登记内容无需撤回。':'previously registered artifacts required no withdrawal.'}</p><details class="correction-operations"><summary>${zh?'查看更正操作':'Inspect correction operations'}</summary><ul>${a.operations.map(o=>`<li><b>${tr(o.operation==='withdraw'?'withdrawOperation':'replaceOperation')}</b> <code>${esc(o.artifact_id)}</code></li>`).join('')}</ul></details><p class="fine-print">${tr('exportNote')}</p>`;
}

function clearPhaseSelection(render=true){
  if(!selectedPhaseId&&!phasePlayback)return;
  selectedPhaseId=null;selectedPhaseData=null;phasePlayback=null;inspectedEvent=null;phaseRenderKey='';
  clearPendingIntent();epoch++;resetRead();
  if(render&&latestState){renderState(latestState);showPendingFacts(false);}
}
