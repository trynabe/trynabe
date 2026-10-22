const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const sandbox = vm.createContext({window:{addEventListener(){}}, console});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../docs/skyline.js'), 'utf8'), sandbox);
const run = code => JSON.parse(JSON.stringify(vm.runInContext(code, sandbox)));

test('newest dates survive ranges longer than 371 days', () => {
  const days=run("normalizeDays([{date:'2024-01-01',count:1},{date:'2026-10-20',count:7}])");
  assert.equal(days.at(-1).date, '2026-10-20');
  assert.equal(days.at(-1).count, 7);
  assert.ok(days.length <= 371);
});
test('impossible calendar dates never create shifted activity', () => {
  const days=run("normalizeDays([{date:'2026-02-28',count:0},{date:'2026-02-30',count:9}])");
  assert.deepEqual(days, [{date:'2026-02-28',count:0}]);
});
test('duplicates aggregate and missing leap day breaks streak', () => {
  const stats=run("computeStats(normalizeDays([{date:'2024-03-01',count:2},{date:'2024-02-28',count:1},{date:'2024-03-01',count:3}]))");
  assert.equal(stats.total,6);assert.equal(stats.longest,1);assert.equal(stats.current,1);
});
test('P95 colors tolerate an outlier while bar height uses true maximum', () => {
  const levels=run('activityLevels([...Array(20)].map((_,i)=>({count:4,date:String(i)})).concat({count:1000,date:"outlier"}))');
  assert.equal(levels[0].level,4);assert.equal(levels.at(-1).level,4);
  assert.ok(vm.runInContext('barHeight(4,1000) < 0.5',sandbox));
  assert.equal(vm.runInContext('barHeight(1000,1000)',sandbox),7.6000000000000005);
});
test('all-zero calendar and yesterday streak are safe',()=>{
  const empty=run("computeStats(normalizeDays([{date:'2026-10-20',count:0}]))");
  assert.equal(empty.total,0);assert.equal(empty.busiest.date,null);assert.equal(empty.current,0);
  assert.equal(run("computeStats(normalizeDays([{date:'2026-10-19',count:2},{date:'2026-10-20',count:0}]))").current,1);
});
test('wave endpoints and projection preserve one grid',()=>{
  assert.equal(vm.runInContext('riseAt(0,52,53,6)',sandbox),0);
  assert.equal(vm.runInContext('riseAt(1,52,53,6)',sandbox),1);
  assert.equal(vm.runInContext('pointInPoly(2,2,[[0,0],[4,0],[4,4],[0,4]])',sandbox),true);
  assert.deepEqual(run('Skyline.prototype.projectRaw(2,3,0,0,Math.PI/2)'),[2,3]);
});
test('unknown, wrong-user or inconsistent payloads cannot show authentic stats',()=>{
  const validate=vm.runInContext('typeof validatePayload === "function" ? validatePayload : (()=>true)',sandbox);
  const valid={username:'trynabe',isDemo:false,generatedAt:'2026-10-20T12:00:00Z',days:[{date:'2026-10-20',count:3}],stats:{total:3}};
  for(const payload of [{...valid,isDemo:undefined},{...valid,username:'demo'},{...valid,stats:{total:99}},{...valid,days:[]}]){
    assert.throws(()=>validate(payload));
  }
  assert.equal(validate(valid).days[0].count,3);
});
