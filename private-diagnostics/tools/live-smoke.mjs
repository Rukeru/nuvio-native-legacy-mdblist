// Explicit deployment-time test only; never called by CI or TV builds.
// Uses synthetic credentials, stores them locally, and always revokes in finally.
import assert from 'node:assert/strict';
import {randomBytes,randomUUID,createHash} from 'node:crypto';
import {mkdirSync,writeFileSync,readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
const config='wrangler.local.jsonc';
const cfg=JSON.parse(readFileSync(config,'utf8'));
assert.equal(cfg.name,'nuvio-diagnostics-api');
assert.equal(cfg.d1_databases[0].database_name,'nuvio-diagnostics');
assert.equal(process.argv[2],'--authorized-live-test','Explicit live-test argument required');
const base='https://nuvio-diagnostics-api.rukeru23.workers.dev';
const hash=s=>createHash('sha256').update(s).digest('hex');
const devices=['tizen','webos'].map(platform=>({platform,id:randomUUID(),code:randomBytes(16).toString('hex'),token:randomBytes(32).toString('hex')}));
mkdirSync('.private',{recursive:true});
const local='.private/live-'+Date.now();
writeFileSync(local+'.json',JSON.stringify(devices),{mode:0o600});
const evidence={started:new Date().toISOString(),endpoint:base,checks:[],synthetic:true};
function sql(command) {
  const r=spawnSync(process.execPath,['node_modules/wrangler/bin/wrangler.js','d1','execute',
    'nuvio-diagnostics','--remote','--config',config,'--command',command,'--json'],{encoding:'utf8',windowsHide:true});
  // Do not echo commands, SQL, auth, or raw API exceptions.
  assert.equal(r.status,0,'Administrative D1 operation failed; inspect local Wrangler log');
  return JSON.parse(r.stdout);
}
async function request(name,path,method,body,expected,token) {
  const r=await fetch(base+path,{method,redirect:'error',signal:AbortSignal.timeout(15000),headers:{
    'content-type':'application/json',...(token?{authorization:token}:{})},
    ...(body===undefined?{}:{body:typeof body==='string'?body:JSON.stringify(body)})});
  assert.equal(r.status,expected,name);
  const result=await r.json();evidence.checks.push({name,status:r.status});return result;
}
try {
  const health=await request('ready','/healthz','GET',undefined,200);assert.equal(health.ready,true);
  await request('unauthenticated rejected','/v1/diagnostics','POST',{},401);
  await request('public read forbidden','/v1/diagnostics','GET',undefined,405);
  await request('public delete forbidden','/v1/diagnostics','DELETE',undefined,405);
  await request('no report index','/v1/reports','GET',undefined,404);
  for(const d of devices) {
    sql(`INSERT INTO enrollment_codes(code_hash,installation_id,platform,expires_at) VALUES('${hash(d.code)}','${d.id}','${d.platform}',${Math.floor(Date.now()/1000)+600});`);
    const paired=await request(d.platform+' pairing','/v1/enroll','POST',{code:d.code,token:d.token,platform:d.platform},200);
    assert.equal(paired.installation_id,d.id);
    const token=`Bearer nv1.${d.id}.${d.token}`;
    const body={version:1,report_id:randomUUID(),platform:d.platform,app_version:'2.0.4.0',
      build_id:'a4dd1afa8f003950df940af7ea216ef478171d8b',events:[{code:'manual_report',context:{count:1}}]};
    const first=await request(d.platform+' synthetic upload','/v1/diagnostics','POST',body,201,token);
    assert.match(first.code,/^[0-9ABCDEFGHJKMNPQRSTVWXYZ]{6}$/);
    const again=await request(d.platform+' duplicate','/v1/diagnostics','POST',body,200,token);assert.deepEqual(again,first);
    await request(d.platform+' changed duplicate rejected','/v1/diagnostics','POST',{...body,events:[{code:'manual_report',context:{count:2}}]},409,token);
    await request(d.platform+' privacy rejection','/v1/diagnostics','POST',{...body,report_id:randomUUID(),private_url:'https://example.invalid/synthetic'},400,token);
    await request(d.platform+' size limit','/v1/diagnostics','POST',' '.repeat(65537),413,token);
    const rows=sql(`SELECT count(*) AS n FROM reports WHERE installation_id='${d.id}' AND receipt_code='${first.code}';`);
    assert.equal(rows[0].results[0].n,1);
    evidence.checks.push({name:d.platform+' D1 persistence',rows:1});
    sql(`UPDATE installations SET revoked=1 WHERE id='${d.id}';`);
    await request(d.platform+' revoked credential rejected','/v1/diagnostics','POST',body,401,token);
  }
  evidence.passed=true;
} finally {
  // A failed assertion cannot leave a valid test upload credential behind.
  sql(`UPDATE installations SET revoked=1 WHERE id IN (${devices.map(d=>"'"+d.id+"'").join(',')});`);
  evidence.finished=new Date().toISOString();
  writeFileSync(local+'-evidence.json',JSON.stringify(evidence,null,2)+'\n');
  console.log(JSON.stringify({passed:!!evidence.passed,checks:evidence.checks.length,evidence:local+'-evidence.json',testCredentialsRevoked:true}));
}
