-- Apply to the EXISTING nuvio-diagnostics database. No personal account data.
CREATE TABLE IF NOT EXISTS installations (
  id TEXT PRIMARY KEY,
  platform TEXT NOT NULL CHECK(platform IN ('tizen','webos')),
  token_hash TEXT NOT NULL CHECK(length(token_hash)=64),
  created_at INTEGER NOT NULL,
  rotated_at INTEGER NOT NULL,
  revoked INTEGER NOT NULL DEFAULT 0 CHECK(revoked IN (0,1))
);
CREATE TABLE IF NOT EXISTS enrollment_codes (
  code_hash TEXT PRIMARY KEY CHECK(length(code_hash)=64),
  installation_id TEXT NOT NULL,
  platform TEXT NOT NULL CHECK(platform IN ('tizen','webos')),
  expires_at INTEGER NOT NULL,
  claimed_hash TEXT,
  claimed_at INTEGER
);
CREATE INDEX IF NOT EXISTS enrollment_expiry ON enrollment_codes(expires_at);
CREATE TABLE IF NOT EXISTS reports (
  id TEXT PRIMARY KEY,
  receipt_code TEXT NOT NULL UNIQUE CHECK(length(receipt_code)=6),
  created_at INTEGER NOT NULL,
  installation_id TEXT NOT NULL REFERENCES installations(id),
  client_report_id TEXT NOT NULL,
  payload_hash TEXT NOT NULL CHECK(length(payload_hash)=64),
  platform TEXT NOT NULL CHECK(platform IN ('tizen','webos')),
  app_version TEXT NOT NULL,
  build_id TEXT NOT NULL,
  severity TEXT NOT NULL CHECK(severity IN ('info','warning','error')),
  category TEXT NOT NULL,
  message TEXT NOT NULL,
  context_json TEXT NOT NULL CHECK(json_valid(context_json) AND length(context_json)<=65536),
  UNIQUE(installation_id,client_report_id)
);
CREATE INDEX IF NOT EXISTS reports_time ON reports(created_at);
CREATE INDEX IF NOT EXISTS reports_installation_time ON reports(installation_id,created_at);
CREATE INDEX IF NOT EXISTS reports_platform_time ON reports(platform,created_at);
CREATE INDEX IF NOT EXISTS reports_severity_time ON reports(severity,created_at);
CREATE INDEX IF NOT EXISTS reports_version_time ON reports(app_version,created_at);
CREATE INDEX IF NOT EXISTS reports_category_time ON reports(category,created_at);
-- Transactional limits, independent of eventually consistent edge rate limiting.
CREATE TRIGGER IF NOT EXISTS installation_cap BEFORE INSERT ON installations
WHEN NOT EXISTS(SELECT 1 FROM installations WHERE id=NEW.id)
 AND (SELECT count(*) FROM installations)>=20
BEGIN SELECT RAISE(ABORT,'installation_quota'); END;
CREATE TRIGGER IF NOT EXISTS report_cap BEFORE INSERT ON reports
BEGIN
  SELECT CASE WHEN (SELECT count(*) FROM reports)>=1500
    THEN RAISE(ABORT,'storage_quota') END;
  SELECT CASE WHEN (SELECT count(*) FROM reports WHERE created_at>NEW.created_at-86400)>=100
    THEN RAISE(ABORT,'global_quota') END;
  SELECT CASE WHEN (SELECT count(*) FROM reports WHERE installation_id=NEW.installation_id
    AND created_at>NEW.created_at-86400)>=20 THEN RAISE(ABORT,'device_quota') END;
END;
