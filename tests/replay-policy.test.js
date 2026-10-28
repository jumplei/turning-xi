const assert=require('node:assert/strict');
const {insightIsFresh}=require('../frontend/replay-policy.js');
const data={second:100,revision:{id:'r1'}};
const snapshot={second:120,revision:{id:'r1'},events:[]};
assert(insightIsFresh(data,snapshot,1,1));
assert(!insightIsFresh(data,snapshot,1,2));
assert(!insightIsFresh(data,{...snapshot,revision:{id:'r2'}},1,1));
assert(!insightIsFresh(data,{...snapshot,second:99},1,1));
assert(!insightIsFresh(data,{...snapshot,second:191},1,1));
for(const event of [{type:'card'},{type:'substitution'},{type:'offside'},{type:'half_time'},{type:'full_time'},{type:'shot',outcome:'goal'},{type:'shot',outcome:'disallowed'}]){
 assert(!insightIsFresh(data,{...snapshot,events:[{...event,second:110}]},1,1));
}
assert(insightIsFresh(data,{...snapshot,events:[{type:'pass',second:110}]},1,1));
assert(!insightIsFresh(data,{...snapshot,navigation_events:[{type:'card',second:110}],events:[]},1,1));
console.log('Replay freshness policy passed.');
const {autoNarrativeMoment}=require('../frontend/replay-policy.js');
assert.equal(autoNarrativeMoment({second:300,events:[{id:'pass',type:'pass',second:300}]},299),null);
assert.equal(autoNarrativeMoment({second:301,events:[{id:'yellow',type:'card',outcome:'yellow',second:301}]},300),null);
const goal={id:'goal',type:'shot',outcome:'goal',second:310};
assert.equal(autoNarrativeMoment({second:330,navigation_events:[goal],events:[]},300).id,'goal');
assert.equal(autoNarrativeMoment({second:340,navigation_events:[goal]},330),null);
assert.equal(autoNarrativeMoment({second:305,navigation_events:[goal]},300),null);
assert.equal(autoNarrativeMoment({second:400,events:[{id:'red',type:'card',outcome:'red',second:400}]},399).id,'red');
console.log('Important-moment scheduling passed.');
