// Offline administrator helper. Never sends a credential or creates a resource.
import {randomBytes,randomUUID,createHash} from 'node:crypto';
import {mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const [platform,existingId]=process.argv.slice(2);
if(!['tizen','webos'].includes(platform) || (existingId && !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(existingId)))
  throw new Error('Usage: node tools/enrollment.mjs tizen|webos [existing-installation-UUID-for-rotation]');
const code=randomBytes(16).toString('hex'),id=existingId||randomUUID();
const digest=createHash('sha256').update(code).digest('hex');
const expires=Math.floor(Date.now()/1000)+600;
const folder=resolve('.private');await mkdir(folder,{recursive:true,mode:0o700});
const stem=resolve(folder,`${platform}-${Date.now()}`);
await writeFile(stem+'.json',JSON.stringify({platform,installation_id:id,pairing_code:code,
  expires_at:new Date(expires*1000).toISOString()},null,2)+'\n',{flag:'wx',mode:0o600});
await writeFile(stem+'.sql',`INSERT INTO enrollment_codes(code_hash,installation_id,platform,expires_at) VALUES('${digest}','${id}','${platform}',${expires});\n`,{flag:'wx',mode:0o600});
console.log('Apply the SQL through the authenticated D1 console:',stem+'.sql');
console.log('Read the pairing code locally; do not paste it into chat or commit it:',stem+'.json');
