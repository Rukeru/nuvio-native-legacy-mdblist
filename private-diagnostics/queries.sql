-- Run individual queries ONLY in Cloudflare's authenticated D1 console.
-- Latest reports
SELECT receipt_code,datetime(created_at,'unixepoch') AS received,platform,app_version,severity,category,message
FROM reports ORDER BY created_at DESC LIMIT 50;
-- Samsung errors
SELECT * FROM reports WHERE platform='tizen' AND severity='error' ORDER BY created_at DESC LIMIT 50;
-- LG errors
SELECT * FROM reports WHERE platform='webos' AND severity='error' ORDER BY created_at DESC LIMIT 50;
-- MDBList events, including reports whose most severe event was another category
SELECT DISTINCT r.* FROM reports r,json_each(r.context_json) e
WHERE json_extract(e.value,'$.code') IN ('mdblist_failed','mdblist_auth') ORDER BY r.created_at DESC LIMIT 50;
-- Account sync and Collections
SELECT * FROM reports WHERE category='account' ORDER BY created_at DESC LIMIT 50;
-- Replace the example app version
SELECT * FROM reports WHERE app_version='2.0.4.63' ORDER BY created_at DESC LIMIT 50;
-- Errors by severity
SELECT severity,count(*) AS reports FROM reports GROUP BY severity;
-- Replace ABCDEF with the six-character TV receipt
SELECT * FROM reports WHERE receipt_code='ABCDEF';
-- Recent performance reports
SELECT * FROM reports WHERE category='performance' AND created_at>=unixepoch()-86400 ORDER BY created_at DESC;
-- Individual report deletion: check the receipt with SELECT first
DELETE FROM reports WHERE receipt_code='ABCDEF';
-- Inspect pseudonymous installations before revoking or rotating a credential
SELECT id,platform,revoked,datetime(rotated_at,'unixepoch') AS rotated FROM installations;
-- Replace the example UUID, then pair again with a NEW enrollment code if needed
UPDATE installations SET revoked=1 WHERE id='00000000-0000-4000-8000-000000000000';
