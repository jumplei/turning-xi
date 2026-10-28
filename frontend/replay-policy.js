'use strict';
// Pure policy shared with offline tests. Replay time includes a half-time interval.
function insightIsFresh(data,snapshot,requestEpoch,currentEpoch){
  if(!snapshot||requestEpoch!==currentEpoch||data.revision?.id!==snapshot.revision?.id)return false;
  if(data.second>snapshot.second||snapshot.second-data.second>90)return false;
  return ![...(snapshot.navigation_events||[]),...(snapshot.events||[])].some(e=>e.second>data.second&&(
    ['card','substitution','offside','half_time','full_time'].includes(e.type)||
    e.type==='shot'&&['goal','disallowed'].includes(e.outcome)));
}
if(typeof module!=='undefined')module.exports={insightIsFresh};

function autoNarrativeMoment(snapshot,fromSecond){
  const candidates=[...(snapshot.navigation_events||[]),...(snapshot.events||[])].filter(e=>e.second>fromSecond&&e.second<=snapshot.second&&(
    e.type==='shot'&&e.outcome==='goal'||e.type==='card'&&(e.card_reason==='second_yellow'||e.outcome==='red')||['half_time','full_time'].includes(e.type)));
  candidates.sort((a,b)=>b.second-a.second);
  return candidates[0]||null;
}
if(typeof module!=='undefined')module.exports.autoNarrativeMoment=autoNarrativeMoment;
