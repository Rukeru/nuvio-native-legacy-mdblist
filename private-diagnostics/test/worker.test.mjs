import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import worker,{sha256,validateReport,MAX_BYTES,RETENTION_SECONDS,EVENTS} from '../ingestion.mjs';

const schema=readFileSync(new URL('../migrations/0001_private_diagnostics.sql',import.meta.url),'utf8');
class D1 {
  constructor(){this.db=new DatabaseSync(':memory:');this.db.exec('PRAGMA foreign_keys=ON;'+schema);this.queries=0;}
  prepare(sql){
    const owner=this;
    return {sql,args:[],bind(...args){this.args=args;return this;},
      async first(){owner.queries++;return owner.db.prepare(sql).get(...this.args)||null;},
      async run(){owner.queries++;return {meta:owner.db.prepare(sql).run(...this.args)};}};
  }
  async batch(statements){
    this.db.exec('BEGIN');
    try {
      const result=statements.map(s=>{this.queries++;const results=this.db.prepare(s.sql).all(...s.args);
        return {success:true,results,meta:{changes:this.db.prepare('SELECT changes() AS n').get().n}};});
      this.db.exec('COMMIT');return result;
    }catch(e){this.db.exec('ROLLBACK');throw e;}
  }
}
function environment(){return {DB:new D1(),INGESTION_ENABLED:'true',
  PAIR_LIMIT:{async limit(){return {success:true};}},UPLOAD_LIMIT:{async limit(){return {success:true};}}};}
function payload(platform='tizen'){return {version:1,report_id:crypto.randomUUID(),platform,
  app_version:'2.0.4.63',build_id:'137a05c5eb124b34b5d2d383d5b58cb35c20da56',
  events:[{code:'sync_failed',context:{http_status:503,attempt:1,profile_slot:0}}]};}
async function request(env,path,body,auth,extra={}){
  const headers={'content-type':'application/json','cf-connecting-ip':'192.0.2.1',...extra.headers};
  if(auth)headers.authorization=auth;
  return worker.fetch(new Request('https://diagnostics.example'+path,{method:'POST',body:JSON.stringify(body),...extra,headers}),env);
}
async function code(env,platform='tizen',id=crypto.randomUUID(),expires=Math.floor(Date.now()/1000)+600){
  const value=crypto.randomUUID().replaceAll('-','');
  env.DB.db.prepare('INSERT INTO enrollment_codes(code_hash,installation_id,platform,expires_at) VALUES(?,?,?,?)')
    .run(await sha256(value),id,platform,expires);
  return {code:value,token:'a'.repeat(64),platform,id};
}
async function pair(env,platform='tizen'){
  const enrollment=await code(env,platform);const {id,...body}=enrollment;
  const res=await request(env,'/v1/enroll',body);assert.equal(res.status,200);
  assert.deepEqual(await res.json(),{version:1,installation_id:id});
  return {id,auth:`Bearer nv1.${id}.${body.token}`,body};
}
function rows(env){return env.DB.db.prepare('SELECT * FROM reports').all();}

test('each platform pairs and uploads; receipt excludes credentials and stores only allowed data',async()=>{
  for(const platform of ['tizen','webos']){
    const env=environment(),device=await pair(env,platform),body=payload(platform);
    const result=await request(env,'/v1/diagnostics',body,device.auth);assert.equal(result.status,201);
    const receipt=await result.json();assert.match(receipt.code,/^[0-9A-HJKMNP-TV-Z]{6}$/);
    assert.deepEqual(Object.keys(receipt).sort(),['code','report_id','version']);
    const stored=rows(env);assert.equal(stored.length,1);assert.equal(stored[0].message,'Account synchronization failed');
    assert.equal(stored[0].platform,platform);assert.equal(stored[0].severity,'error');
    assert.equal(JSON.stringify(stored).includes(device.body.token),false);
    assert.equal(result.headers.get('cache-control'),'no-store');
  }
});
test('no authorization, wrong token, unknown device and revoked device cannot upload',async()=>{
  const env=environment(),device=await pair(env);
  for(const auth of [undefined,device.auth.replace(/a{64}$/,'b'.repeat(64)),`Bearer nv1.${crypto.randomUUID()}.${'a'.repeat(64)}`])
    assert.equal((await request(env,'/v1/diagnostics',payload(),auth)).status,401);
  env.DB.db.prepare('UPDATE installations SET revoked=1 WHERE id=?').run(device.id);
  assert.equal((await request(env,'/v1/diagnostics',payload(),device.auth)).status,401);
  assert.equal((await request(env,'/v1/enroll',device.body)).status,401,'used code cannot undo revocation');
  assert.equal(rows(env).length,0);
});
test('enrollment expires, is platform bound, and cannot be claimed with another secret',async()=>{
  const env=environment(),expired=await code(env,'tizen',crypto.randomUUID(),1);
  delete expired.id;assert.equal((await request(env,'/v1/enroll',expired)).status,401);
  const device=await pair(env);
  assert.equal((await request(env,'/v1/enroll',{...device.body,token:'b'.repeat(64)})).status,401);
  assert.equal((await request(env,'/v1/enroll',{...device.body,platform:'webos'})).status,401);
  assert.equal((await request(env,'/v1/enroll',device.body)).status,200,'lost response retry');
});
test('rotation invalidates old token and an old enrollment cannot roll it back',async()=>{
  const env=environment(),device=await pair(env),replacement=await code(env,'tizen',device.id);
  delete replacement.id;replacement.token='b'.repeat(64);
  assert.equal((await request(env,'/v1/enroll',replacement)).status,200);
  assert.equal((await request(env,'/v1/enroll',device.body)).status,401);
  assert.equal((await request(env,'/v1/diagnostics',payload(),device.auth)).status,401);
  assert.equal((await request(env,'/v1/diagnostics',payload(),`Bearer nv1.${device.id}.${replacement.token}`)).status,201);
  assert.equal(env.DB.db.prepare('SELECT count(*) AS n FROM installations').get().n,1);
});
test('duplicate delivery is idempotent; changed payload using the same ID conflicts',async()=>{
  const env=environment(),device=await pair(env),body=payload();
  const first=await request(env,'/v1/diagnostics',body,device.auth);const receipt=await first.json();
  const duplicate=await request(env,'/v1/diagnostics',body,device.auth);
  assert.equal(duplicate.status,200);assert.deepEqual(await duplicate.json(),receipt);
  body.events[0].context.http_status=401;
  assert.equal((await request(env,'/v1/diagnostics',body,device.auth)).status,409);assert.equal(rows(env).length,1);
});
test('strict privacy allowlist rejects raw text, nested credentials, URL, title and malformed values',async()=>{
  const env=environment(),device=await pair(env);
  const mutations=[
    p=>p.log='secret log',p=>p.api_key='private',p=>p.events[0].message='title',
    p=>p.events[0].context.url='https://private/token',p=>p.events[0].context.http_status='503',
    p=>p.events[0].context.profile_slot={token:'secret'},p=>p.events[0].context.profile_slot=-1,
    p=>p.events[0].context.http_status=99,p=>p.events[0].code='__proto__',
    p=>p.events[0].context.authorization='Bearer secret',p=>p.events=[],
    p=>p.events=Array.from({length:33},()=>({code:'manual_report',context:{}})),
    p=>p.report_id=[p.report_id],p=>p.build_id='https://private',p=>p.app_version='my@email.example'
  ];
  for(const change of mutations){const p=payload();change(p);const res=await request(env,'/v1/diagnostics',p,device.auth);
    assert.equal(res.status,400,JSON.stringify(p));}
  assert.equal(rows(env).length,0);
  for(const event of Object.keys(EVENTS))assert.doesNotThrow(()=>validateReport({...payload(),events:[{code:event,context:{}}]}));
});
test('size, encoding, content type, invalid UTF-8 and malformed JSON are rejected',async()=>{
  const env=environment(),device=await pair(env);
  assert.equal((await request(env,'/v1/diagnostics',{oversize:'x'.repeat(MAX_BYTES)},device.auth)).status,413);
  assert.equal((await request(env,'/v1/diagnostics',payload(),device.auth,{headers:{'content-length':String(MAX_BYTES+1)}})).status,413);
  for(const headers of [{'content-type':'text/plain'},{'content-encoding':'gzip'}])
    assert.equal((await request(env,'/v1/diagnostics',payload(),device.auth,{headers})).status,415);
  for(const body of ['{',new Uint8Array([0xff,0xff])]){
    const res=await worker.fetch(new Request('https://diagnostics.example/v1/diagnostics',{method:'POST',body,
      headers:{'content-type':'application/json',authorization:device.auth}}),env);assert.equal(res.status,400);
  }
});
test('edge limits run before database lookup and missing configuration fails closed',async()=>{
  const env=environment();env.PAIR_LIMIT.limit=async()=>({success:false});
  const res=await request(env,'/v1/enroll',{});assert.equal(res.status,429);assert.equal(env.DB.queries,0);
  env.INGESTION_ENABLED='false';assert.equal((await request(env,'/v1/diagnostics',{})).status,503);
  env.INGESTION_ENABLED='true';delete env.UPLOAD_LIMIT;assert.equal((await request(env,'/v1/enroll',{})).status,503);
});
test('hard per-device and global quotas are transactional and duplicates do not consume quota',async()=>{
  const env=environment();let firstDevice,firstPayload;
  for(let d=0;d<5;d++){
    const device=await pair(env);if(!d)firstDevice=device;
    for(let n=0;n<20;n++){
      const body=payload();if(!d&&!n)firstPayload=body;
      assert.equal((await request(env,'/v1/diagnostics',body,device.auth)).status,201);
    }
    assert.equal((await request(env,'/v1/diagnostics',payload(),device.auth)).status,429);
  }
  const sixth=await pair(env);assert.equal((await request(env,'/v1/diagnostics',payload(),sixth.auth)).status,429);
  assert.equal((await request(env,'/v1/diagnostics',firstPayload,firstDevice.auth)).status,200);
  assert.equal(rows(env).length,100);
});
test('installation cap prevents unbounded persistent enrollment',async()=>{
  const env=environment();for(let n=0;n<20;n++)await pair(env);
  const body=await code(env);delete body.id;
  assert.equal((await request(env,'/v1/enroll',body)).status,429);
  assert.equal(env.DB.db.prepare('SELECT count(*) AS n FROM installations').get().n,20);
  assert.equal(env.DB.db.prepare('SELECT claimed_hash FROM enrollment_codes WHERE code_hash=?').get(await sha256(body.code)).claimed_hash,null);
});
test('retention removes only expired reports and enrollment codes',async()=>{
  const env=environment(),device=await pair(env),now=Math.floor(Date.now()/1000);
  await request(env,'/v1/diagnostics',payload(),device.auth);
  env.DB.db.prepare('UPDATE reports SET created_at=?').run(now-RETENTION_SECONDS-1);
  await request(env,'/v1/diagnostics',payload(),device.auth);
  await code(env,'webos',crypto.randomUUID(),now-1);
  await worker.scheduled({},env);
  assert.equal(rows(env).length,1);
  assert.equal(env.DB.db.prepare('SELECT count(*) AS n FROM enrollment_codes WHERE expires_at<?').get(now).n,0);
  assert.equal(env.DB.db.prepare('SELECT count(*) AS n FROM installations').get().n,1);
});
test('storage remains bounded even if retention stops running',async()=>{
  const env=environment(),device=await pair(env),now=Math.floor(Date.now()/1000);
  const insert=env.DB.db.prepare(`INSERT INTO reports VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)`);
  for(let i=0;i<1500;i++)insert.run(crypto.randomUUID(),String(i).padStart(6,'0'),now-(2000-i)*86400,
    device.id,crypto.randomUUID(),'b'.repeat(64),'tizen','2.0.4','c'.repeat(40),'info','diagnostics','Manual diagnostic report','[]');
  assert.equal((await request(env,'/v1/diagnostics',payload(),device.auth)).status,429);
  await worker.scheduled({},env);assert.equal(rows(env).length,0);
  assert.equal((await request(env,'/v1/diagnostics',payload(),device.auth)).status,201);
});
test('platform identity cannot be changed and no public read/delete/admin routes exist',async()=>{
  const env=environment(),device=await pair(env);
  assert.equal((await request(env,'/v1/diagnostics',payload('webos'),device.auth)).status,400);
  for(const path of ['/v1/reports','/v1/admin','/v1/diagnostics/ABCDEF'])
    assert.equal((await worker.fetch(new Request('https://diagnostics.example'+path,{headers:{authorization:device.auth}}),env)).status,404);
  for(const method of ['GET','DELETE','OPTIONS'])assert.equal((await worker.fetch(new Request('https://diagnostics.example/v1/diagnostics',{method}),env)).status,405);
  assert.equal((await worker.fetch(new Request('http://diagnostics.example/healthz'),env)).status,400);
  assert.equal((await worker.fetch(new Request('https://diagnostics.example/healthz?token=secret'),env)).status,400);
});
test('database outages return safe errors without exception details or fallback transport',async()=>{
  const env=environment(),device=await pair(env);
  env.DB.prepare=()=>{throw new Error('database has PRIVATE-TOKEN');};
  const res=await request(env,'/v1/diagnostics',payload(),device.auth);
  assert.equal(res.status,503);assert.deepEqual(await res.json(),{error:'service_unavailable'});
});
test('concurrent enrollment claims do not replace the winning installation credential',async()=>{
  const env=environment(),enrollment=await code(env);delete enrollment.id;
  const replies=await Promise.all([request(env,'/v1/enroll',enrollment),
    request(env,'/v1/enroll',{...enrollment,token:'b'.repeat(64)})]);
  assert.deepEqual(replies.map(r=>r.status).sort(),[200,401]);
  assert.equal(env.DB.db.prepare('SELECT count(*) AS n FROM installations').get().n,1);
});
test('concurrent duplicate reports create one row and return the same receipt',async()=>{
  const env=environment(),device=await pair(env),body=payload();
  const replies=await Promise.all(Array.from({length:8},()=>request(env,'/v1/diagnostics',body,device.auth)));
  assert.equal(replies.filter(r=>r.status===201).length,1);
  assert.equal(replies.filter(r=>r.status===200).length,7);
  const codes=await Promise.all(replies.map(async r=>(await r.json()).code));
  assert.equal(new Set(codes).size,1);assert.equal(rows(env).length,1);
});
test('revocation between initial authorization and write prevents persistence',async()=>{
  const env=environment(),device=await pair(env),batch=env.DB.batch.bind(env.DB);
  env.DB.batch=async statements=>{
    env.DB.db.prepare('UPDATE installations SET revoked=1 WHERE id=?').run(device.id);
    return batch(statements);
  };
  assert.equal((await request(env,'/v1/diagnostics',payload(),device.auth)).status,401);
  assert.equal(rows(env).length,0);
});
test('a failed enrollment transaction leaves neither a device nor a claimed code',async()=>{
  const env=environment(),enrollment=await code(env);delete enrollment.id;
  const batch=env.DB.batch.bind(env.DB);
  env.DB.batch=statements=>batch([statements[0],env.DB.prepare('SELECT missing_column FROM installations')]);
  assert.equal((await request(env,'/v1/enroll',enrollment)).status,503);
  assert.equal(env.DB.db.prepare('SELECT count(*) AS n FROM installations').get().n,0);
  assert.equal(env.DB.db.prepare('SELECT claimed_hash FROM enrollment_codes').get().claimed_hash,null);
});
