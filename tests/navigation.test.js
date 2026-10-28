// Run with node tests/navigation.test.js. No packages or network required.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const sandbox={};vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('frontend/navigation.js','utf8')+'\nthis.items=navigationItems;',sandbox);
const metadata={key_moments:[{key:'goal',second:100},{key:'red_card',second:200},{key:'second_yellow',second:200},{key:'full_time',second:300}]};
const kickoff={second:0,revision:{id:'r1'},navigation_events:[],phases:[]};
assert.equal(sandbox.items(kickoff,metadata).length,0,'Future metadata must not populate normal navigation');
assert.equal(sandbox.items(kickoff,metadata,true).length,0,'Navigation never exposes future shortcuts');
const later={second:150,revision:{id:'r1'},navigation_events:[{id:'g1',type:'shot',outcome:'goal',second:100,team:'home'},{id:'r1',type:'card',outcome:'red',second:200,team:'away'}],phases:[{id:'p1',end:120,team:'home',kind:'sustained_pressure'},{id:'p2',end:210,team:'away',kind:'recovery_to_shot'}]};
assert.equal(sandbox.items(later,metadata).length,2);
assert.ok(sandbox.items(later,metadata).every(i=>i.second<=150));
const rewind={...later,second:50};assert.equal(sandbox.items(rewind,metadata).length,0,'Rewind must remove known future moments');
const corrected={...later,navigation_events:[{...later.navigation_events[0],outcome:'disallowed'}],phases:[]};
assert.equal(sandbox.items(corrected,metadata)[0].kind,'disallowed');
assert.equal(sandbox.items(later,metadata)[0].category,'match');
console.log('Navigation checks passed: no future spoilers, rewind, groups, corrected goal.');
