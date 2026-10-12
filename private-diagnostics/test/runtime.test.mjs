import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {Miniflare,convertV4MiniflareOptions} from 'miniflare';
import {unstable_splitSqlQuery as splitSqlQuery} from 'wrangler';
import {sha256} from '../ingestion.mjs';

test('real Workers runtime and D1 execute enrollment, transactional ingestion and retention',async()=>{
  const runtime=new Miniflare(convertV4MiniflareOptions({modulesRoot:fileURLToPath(new URL('..',import.meta.url)),
    modules:['worker.mjs','ingestion.mjs'].map(name=>({type:'ESModule',path:fileURLToPath(new URL('../'+name,import.meta.url))})),
    compatibilityDate:'2026-10-01',bindings:{INGESTION_ENABLED:'true'},d1Databases:['DB'],
    ratelimits:{PAIR_LIMIT:{namespace_id:'7263101',simple:{limit:5,period:60}},
      UPLOAD_LIMIT:{namespace_id:'7263102',simple:{limit:30,period:60}}}}));
  try {
    const db=await runtime.getD1Database('DB');
    // Use Wrangler's migration splitter: D1 exec treats each LINE as a statement.
    const statements=splitSqlQuery(readFileSync(new URL('../migrations/0001_private_diagnostics.sql',import.meta.url),'utf8'));
    await db.batch(statements.map(sql=>db.prepare(sql)));
    const id=crypto.randomUUID(),code='d'.repeat(32),token='e'.repeat(64);
    await db.prepare('INSERT INTO enrollment_codes VALUES(?,?,?,?,NULL,NULL)').bind(await sha256(code),id,'tizen',Math.floor(Date.now()/1000)+600).run();
    const post=(path,body,auth)=>runtime.dispatchFetch('https://diagnostics.example'+path,{method:'POST',
      headers:{'content-type':'application/json','cf-connecting-ip':'192.0.2.4',...(auth?{authorization:auth}:{})},body:JSON.stringify(body)});
    const paired=await post('/v1/enroll',{code,token,platform:'tizen'});
    assert.equal(paired.status,200);assert.equal((await paired.json()).installation_id,id);
    const auth=`Bearer nv1.${id}.${token}`;
    const body={version:1,report_id:crypto.randomUUID(),platform:'tizen',app_version:'2.0.4.63',
      build_id:'f'.repeat(40),events:[{code:'manual_report',context:{count:1}}]};
    const first=await post('/v1/diagnostics',body,auth);assert.equal(first.status,201);
    const received=await first.json();const duplicate=await post('/v1/diagnostics',body,auth);
    assert.equal(duplicate.status,200);assert.deepEqual(await duplicate.json(),received);
    assert.equal((await db.prepare('SELECT count(*) AS n FROM reports').first()).n,1);
    await db.prepare('UPDATE reports SET created_at=0').run();
    const worker=await runtime.getWorker();await worker.scheduled();
    assert.equal((await db.prepare('SELECT count(*) AS n FROM reports').first()).n,0);
    await db.prepare('UPDATE installations SET revoked=1').run();
    assert.equal((await post('/v1/diagnostics',body,auth)).status,401);
  } finally { await runtime.dispose(); }
});
