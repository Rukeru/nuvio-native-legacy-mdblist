// Upload-only API implementation. No public read, search, delete or admin route.
export const MAX_BYTES = 65536;
export const RETENTION_SECONDS = 14 * 86400;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const HEX64 = /^[0-9a-f]{64}$/;
const VERSION = /^\d{1,3}(?:\.\d{1,6}){2,3}$/;
const RANGES = { http_status:[0,599], attempt:[0,8], profile_slot:[0,10],
  elapsed_ms:[0,300000], age_minutes:[0,43200], count:[1,100000],
  fps:[0,240], frame_ms:[0,10000], memory_mb:[0,32768], error_code:[0,999] };
// Messages and severity are server-owned. No user text, raw logs, URLs or titles.
export const EVENTS = Object.freeze({
  manual_report:['diagnostics','info','Manual diagnostic report',['count']],
  previous_session_ended:['playback','warning','Previous session ended unexpectedly',['count']],
  sync_failed:['account','error','Account synchronization failed',['http_status','attempt','profile_slot','elapsed_ms']],
  sync_cached:['account','warning','Account data used a cached fallback',['profile_slot','age_minutes']],
  sync_stale:['account','warning','Collection refresh detected stale data',['profile_slot','age_minutes']],
  manifest_failed:['account','warning','Addon manifest could not be refreshed',['http_status','attempt']],
  mdblist_failed:['mdblist','error','MDBList tracking request failed',['http_status','attempt']],
  mdblist_auth:['mdblist','error','MDBList authentication needs attention',['http_status']],
  trakt_failed:['trakt','error','Trakt tracking request failed',['http_status','attempt']],
  tracking_retry:['tracking','warning','Tracking request queued for retry',['attempt','count']],
  tracking_duplicate:['tracking','info','Duplicate tracking event suppressed',['count']],
  account_refresh_failed:['account','error','Account credential refresh failed',['http_status']],
  playback_init:['playback','error','Playback could not initialize',['error_code']],
  playback_decoder:['playback','error','Decoder reported a failure',['error_code']],
  playback_interrupted:['playback','warning','Playback ended unexpectedly',['error_code']],
  performance_slow:['performance','warning','Sustained slow rendering detected',['fps','frame_ms','count']],
  performance_memory:['performance','warning','Memory pressure detected',['memory_mb']],
  sync_slow:['performance','warning','Applying account data was slow',['elapsed_ms']]
});
class Rejection extends Error {
  constructor(status,code,retry=0) { super(code); this.status=status; this.code=code; this.retry=retry; }
}
const reject=(status,code,retry=0)=>{ throw new Rejection(status,code,retry); };
const object=v=>v!==null && typeof v==='object' && !Array.isArray(v);
function keys(value,expected) {
  if(!object(value) || Object.keys(value).sort().join('|')!==[...expected].sort().join('|'))
    reject(400,'invalid_schema');
}
export async function sha256(value) {
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value));
  return Array.from(new Uint8Array(bytes),v=>v.toString(16).padStart(2,'0')).join('');
}
function response(status,value,retry=0) {
  const headers={'content-type':'application/json','cache-control':'no-store',
    'x-content-type-options':'nosniff','strict-transport-security':'max-age=31536000'};
  if(retry)headers['retry-after']=String(retry);
  return new Response(JSON.stringify(value),{status,headers});
}
async function readJSON(request,max=MAX_BYTES) {
  if(request.headers.get('content-type')?.split(';')[0].trim()!=='application/json')reject(415,'json_required');
  if(request.headers.has('content-encoding'))reject(415,'encoding_unsupported');
  const length=request.headers.get('content-length');
  if(length!==null && (!/^\d+$/.test(length) || Number(length)>max))reject(413,'payload_too_large');
  if(!request.body)reject(400,'invalid_json');
  const reader=request.body.getReader();const chunks=[];let size=0;
  try {
    for(;;) {
      const {done,value}=await reader.read();if(done)break;
      size+=value.byteLength;
      if(size>max){await reader.cancel();reject(413,'payload_too_large');}
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const body=new Uint8Array(size);let offset=0;
  for(const chunk of chunks){body.set(chunk,offset);offset+=chunk.byteLength;}
  try { return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(body)); }
  catch { reject(400,'invalid_json'); }
}
export function validateReport(v) {
  keys(v,['version','report_id','platform','app_version','build_id','events']);
  if(v.version!==1 || typeof v.report_id!=='string' || !UUID.test(v.report_id) || !['tizen','webos'].includes(v.platform)
    || typeof v.app_version!=='string' || !VERSION.test(v.app_version)
    || typeof v.build_id!=='string' || !/^[0-9a-f]{40}$/.test(v.build_id)
    || !Array.isArray(v.events) || v.events.length<1 || v.events.length>32)reject(400,'invalid_schema');
  let severity='info',category='diagnostics',message='Manual diagnostic report';
  const rank={info:0,warning:1,error:2};
  const events=v.events.map(event=>{
    keys(event,['code','context']);
    if(typeof event.code!=='string' || !Object.hasOwn(EVENTS,event.code) || !object(event.context))reject(400,'invalid_event');
    const [cat,sev,msg,allowed]=EVENTS[event.code];const context={};
    for(const key of Object.keys(event.context).sort()) {
      if(!allowed.includes(key))reject(400,'invalid_context');
      const n=event.context[key],range=RANGES[key];
      if(!Number.isSafeInteger(n)||n<range[0]||n>range[1])reject(400,'invalid_context');
      if(key==='http_status' && n!==0 && n<100)reject(400,'invalid_context');
      context[key]=n;
    }
    if(rank[sev]>rank[severity] || category==='diagnostics'){category=cat;severity=sev;message=msg;}
    return {code:event.code,context};
  });
  return {canonical:{version:1,report_id:v.report_id,platform:v.platform,
    app_version:v.app_version,build_id:v.build_id,events},severity,category,message};
}
async function limit(binding,key) {
  if(!binding || !(await binding.limit({key})).success)reject(429,'rate_limited',60);
}
function receipt() {
  const alphabet='0123456789ABCDEFGHJKMNPQRSTVWXYZ';
  return Array.from(crypto.getRandomValues(new Uint8Array(6)),v=>alphabet[v&31]).join('');
}
async function enroll(request,env,now) {
  const v=await readJSON(request,1024);keys(v,['code','token','platform']);
  if(typeof v.code!=='string'||!/^[0-9a-f]{32}$/.test(v.code)||typeof v.token!=='string'||!HEX64.test(v.token)
    || !['tizen','webos'].includes(v.platform))reject(400,'invalid_enrollment');
  const codeHash=await sha256(v.code),tokenHash=await sha256(v.token);
  const found=await env.DB.prepare('SELECT installation_id,platform FROM enrollment_codes WHERE code_hash=? AND expires_at>=?')
    .bind(codeHash,now).first();
  if(!found||found.platform!==v.platform)reject(401,'enrollment_rejected');
  // A lost response may be retried with the SAME locally persisted secret.
  // A previously claimed code cannot roll back a later credential rotation.
  const statements=[
    env.DB.prepare(`INSERT INTO installations(id,platform,token_hash,created_at,rotated_at,revoked)
      SELECT installation_id,platform,?,?,?,0 FROM enrollment_codes
      WHERE code_hash=? AND expires_at>=? AND platform=?
      AND (claimed_hash IS NULL OR (claimed_hash=? AND EXISTS
        (SELECT 1 FROM installations i WHERE i.id=installation_id AND i.token_hash=? AND i.revoked=0)))
      ON CONFLICT(id) DO UPDATE SET token_hash=excluded.token_hash,rotated_at=excluded.rotated_at,revoked=0
      WHERE installations.platform=excluded.platform`)
      .bind(tokenHash,now,now,codeHash,now,v.platform,tokenHash,tokenHash),
    env.DB.prepare(`UPDATE enrollment_codes SET claimed_hash=?,claimed_at=COALESCE(claimed_at,?)
      WHERE code_hash=? AND expires_at>=? AND (claimed_hash IS NULL OR claimed_hash=?)
      AND EXISTS(SELECT 1 FROM installations WHERE id=enrollment_codes.installation_id AND token_hash=? AND revoked=0)`)
      .bind(tokenHash,now,codeHash,now,tokenHash,tokenHash)
  ];
  const result=await env.DB.batch(statements);
  if(result[0].meta.changes!==1 || result[1].meta.changes!==1)reject(401,'enrollment_rejected');
  return response(200,{version:1,installation_id:found.installation_id});
}
async function ingest(request,env,now) {
  const match=/^Bearer nv1\.([0-9a-f-]{36})\.([0-9a-f]{64})$/.exec(request.headers.get('authorization')||'');
  if(!match||!UUID.test(match[1]))reject(401,'unauthorized');
  const id=match[1],tokenHash=await sha256(match[2]);
  const device=await env.DB.prepare('SELECT platform FROM installations WHERE id=? AND token_hash=? AND revoked=0')
    .bind(id,tokenHash).first();
  if(!device)reject(401,'unauthorized');
  await limit(env.UPLOAD_LIMIT,'device:'+id);
  const {canonical:v,severity,category,message}=validateReport(await readJSON(request));
  if(v.platform!==device.platform)reject(400,'platform_mismatch');
  const canonical=JSON.stringify(v),payloadHash=await sha256(canonical);
  for(let attempt=0;attempt<3;attempt++) {
    const code=receipt();
    try {
      const result=await env.DB.batch([
        env.DB.prepare(`INSERT INTO reports(id,receipt_code,created_at,installation_id,client_report_id,payload_hash,
          platform,app_version,build_id,severity,category,message,context_json)
          SELECT ?,?,?,?,?,?,?,?,?,?,?,?,? WHERE EXISTS
            (SELECT 1 FROM installations WHERE id=? AND token_hash=? AND revoked=0)
          AND NOT EXISTS(SELECT 1 FROM reports WHERE installation_id=? AND client_report_id=?)`)
          .bind(crypto.randomUUID(),code,now,id,v.report_id,payloadHash,v.platform,v.app_version,v.build_id,
            severity,category,message,JSON.stringify(v.events),id,tokenHash,id,v.report_id),
        env.DB.prepare(`SELECT r.id,r.receipt_code,r.payload_hash FROM reports r JOIN installations i ON i.id=r.installation_id
          WHERE r.installation_id=? AND r.client_report_id=? AND i.token_hash=? AND i.revoked=0`)
          .bind(id,v.report_id,tokenHash)
      ]);
      const stored=result[1].results[0];
      if(!stored)reject(401,'unauthorized');
      if(stored.payload_hash!==payloadHash)reject(409,'idempotency_conflict');
      return response(result[0].meta.changes?201:200,{version:1,report_id:stored.id,code:stored.receipt_code});
    } catch(error) {
      if(/UNIQUE constraint failed: reports\.receipt_code/.test(String(error)))continue;
      throw error;
    }
  }
  reject(503,'receipt_unavailable',60);
}
export default {
  async fetch(request,env) {
    try {
      const url=new URL(request.url);
      if(url.protocol!=='https:')reject(400,'https_required');
      if(url.search)reject(400,'query_unsupported');
      const ready=env.INGESTION_ENABLED==='true' && !!env.DB && !!env.PAIR_LIMIT && !!env.UPLOAD_LIMIT;
      if(url.pathname==='/healthz' && request.method==='GET')return response(200,{version:1,ready});
      if(!['/v1/enroll','/v1/diagnostics'].includes(url.pathname))reject(404,'not_found');
      if(request.method!=='POST')reject(405,'method_not_allowed');
      if(!ready)reject(503,'not_ready',3600);
      // Coarse abuse protection before any D1 query; separate authenticated device limits follow.
      const ip=await sha256(request.headers.get('cf-connecting-ip')||'unknown');
      await limit(url.pathname==='/v1/enroll'?env.PAIR_LIMIT:env.UPLOAD_LIMIT,'ip:'+ip);
      const now=Math.floor(Date.now()/1000);
      return await (url.pathname==='/v1/enroll'?enroll:ingest)(request,env,now);
    } catch(error) {
      if(error instanceof Rejection)return response(error.status,{error:error.code},error.retry);
      if(/(?:global|device|storage|installation)_quota/.test(String(error)))return response(429,{error:'quota_exceeded'},3600);
      // No raw database exception, request headers, body, IP or credential logging.
      return response(503,{error:'service_unavailable'},60);
    }
  },
  async scheduled(_controller,env) {
    const now=Math.floor(Date.now()/1000);
    await env.DB.batch([
      env.DB.prepare('DELETE FROM reports WHERE created_at<?').bind(now-RETENTION_SECONDS),
      env.DB.prepare('DELETE FROM enrollment_codes WHERE expires_at<?').bind(now)
    ]);
  }
};
