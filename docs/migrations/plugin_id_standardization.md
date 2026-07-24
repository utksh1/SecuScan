# Migration & Rollback Guide: Plugin ID Standardization

This document details the database migration and rollback paths for standardizing plugin IDs to a snake_case naming convention.

## Migration Path

The migration is automatically executed when the backend is started. The process is handled by the `Database.connect` routine, which runs all SQL scripts in `backend/secuscan/migrations/`.

### Migration Operations
The migration script (`007_standardize_plugin_ids.sql`) performs `UPDATE` operations on the following tables to rename legacy (hyphenated or non-standard) plugin IDs to their new canonical snake_case representations:
- `tasks`
- `findings`
- `crawl_runs`
- `asset_services`
- `audit_log`
- `presets`
- `plugins`

For example:
- `domain-finder` is renamed to `domain_finder`.
- `website-recon-2` is renamed to `website_recon`.
- `waf-detection` is renamed/standardized to `waf_detector`.

## Rollback Path

If you need to roll back the migration, execute the following SQL script against the SQLite database:

```sql
-- 1. Revert plugins in tasks table
UPDATE tasks SET plugin_id = 'domain-finder' WHERE plugin_id = 'domain_finder';
UPDATE tasks SET plugin_id = 'google-dorking' WHERE plugin_id = 'google_dorking';
UPDATE tasks SET plugin_id = 'people-email-discovery' WHERE plugin_id = 'people_email_discovery';
UPDATE tasks SET plugin_id = 'port-scanner' WHERE plugin_id = 'port_scanner';
UPDATE tasks SET plugin_id = 'subdomain-finder' WHERE plugin_id = 'subdomain_finder';
UPDATE tasks SET plugin_id = 'url-fuzzer-2' WHERE plugin_id = 'url_fuzzer';
UPDATE tasks SET plugin_id = 'virtual-host-finder' WHERE plugin_id = 'virtual_host_finder';
UPDATE tasks SET plugin_id = 'website-recon-2' WHERE plugin_id = 'website_recon';
UPDATE tasks SET plugin_id = 'waf-detection' WHERE plugin_id = 'waf_detector';

-- 2. Revert plugins in findings table
UPDATE findings SET plugin_id = 'domain-finder' WHERE plugin_id = 'domain_finder';
UPDATE findings SET plugin_id = 'google-dorking' WHERE plugin_id = 'google_dorking';
UPDATE findings SET plugin_id = 'people-email-discovery' WHERE plugin_id = 'people_email_discovery';
UPDATE findings SET plugin_id = 'port-scanner' WHERE plugin_id = 'port_scanner';
UPDATE findings SET plugin_id = 'subdomain-finder' WHERE plugin_id = 'subdomain_finder';
UPDATE findings SET plugin_id = 'url-fuzzer-2' WHERE plugin_id = 'url_fuzzer';
UPDATE findings SET plugin_id = 'virtual-host-finder' WHERE plugin_id = 'virtual_host_finder';
UPDATE findings SET plugin_id = 'website-recon-2' WHERE plugin_id = 'website_recon';
UPDATE findings SET plugin_id = 'waf-detection' WHERE plugin_id = 'waf_detector';

-- 3. Revert plugins in crawl_runs table
UPDATE crawl_runs SET plugin_id = 'domain-finder' WHERE plugin_id = 'domain_finder';
UPDATE crawl_runs SET plugin_id = 'google-dorking' WHERE plugin_id = 'google_dorking';
UPDATE crawl_runs SET plugin_id = 'people-email-discovery' WHERE plugin_id = 'people_email_discovery';
UPDATE crawl_runs SET plugin_id = 'port-scanner' WHERE plugin_id = 'port_scanner';
UPDATE crawl_runs SET plugin_id = 'subdomain-finder' WHERE plugin_id = 'subdomain_finder';
UPDATE crawl_runs SET plugin_id = 'url-fuzzer-2' WHERE plugin_id = 'url_fuzzer';
UPDATE crawl_runs SET plugin_id = 'virtual-host-finder' WHERE plugin_id = 'virtual_host_finder';
UPDATE crawl_runs SET plugin_id = 'website-recon-2' WHERE plugin_id = 'website_recon';
UPDATE crawl_runs SET plugin_id = 'waf-detection' WHERE plugin_id = 'waf_detector';

-- 4. Revert plugins in asset_services table
UPDATE asset_services SET plugin_id = 'domain-finder' WHERE plugin_id = 'domain_finder';
UPDATE asset_services SET plugin_id = 'google-dorking' WHERE plugin_id = 'google_dorking';
UPDATE asset_services SET plugin_id = 'people-email-discovery' WHERE plugin_id = 'people_email_discovery';
UPDATE asset_services SET plugin_id = 'port-scanner' WHERE plugin_id = 'port_scanner';
UPDATE asset_services SET plugin_id = 'subdomain-finder' WHERE plugin_id = 'subdomain_finder';
UPDATE asset_services SET plugin_id = 'url-fuzzer-2' WHERE plugin_id = 'url_fuzzer';
UPDATE asset_services SET plugin_id = 'virtual-host-finder' WHERE plugin_id = 'virtual_host_finder';
UPDATE asset_services SET plugin_id = 'website-recon-2' WHERE plugin_id = 'website_recon';
UPDATE asset_services SET plugin_id = 'waf-detection' WHERE plugin_id = 'waf_detector';

-- 5. Revert plugins in audit_log table
UPDATE audit_log SET plugin_id = 'domain-finder' WHERE plugin_id = 'domain_finder';
UPDATE audit_log SET plugin_id = 'google-dorking' WHERE plugin_id = 'google_dorking';
UPDATE audit_log SET plugin_id = 'people-email-discovery' WHERE plugin_id = 'people_email_discovery';
UPDATE audit_log SET plugin_id = 'port-scanner' WHERE plugin_id = 'port_scanner';
UPDATE audit_log SET plugin_id = 'subdomain-finder' WHERE plugin_id = 'subdomain_finder';
UPDATE audit_log SET plugin_id = 'url-fuzzer-2' WHERE plugin_id = 'url_fuzzer';
UPDATE audit_log SET plugin_id = 'virtual-host-finder' WHERE plugin_id = 'virtual_host_finder';
UPDATE audit_log SET plugin_id = 'website-recon-2' WHERE plugin_id = 'website_recon';
UPDATE audit_log SET plugin_id = 'waf-detection' WHERE plugin_id = 'waf_detector';

-- 6. Revert plugins in presets table
UPDATE presets SET plugin_id = 'domain-finder' WHERE plugin_id = 'domain_finder';
UPDATE presets SET plugin_id = 'google-dorking' WHERE plugin_id = 'google_dorking';
UPDATE presets SET plugin_id = 'people-email-discovery' WHERE plugin_id = 'people_email_discovery';
UPDATE presets SET plugin_id = 'port-scanner' WHERE plugin_id = 'port_scanner';
UPDATE presets SET plugin_id = 'subdomain-finder' WHERE plugin_id = 'subdomain_finder';
UPDATE presets SET plugin_id = 'url-fuzzer-2' WHERE plugin_id = 'url_fuzzer';
UPDATE presets SET plugin_id = 'virtual-host-finder' WHERE plugin_id = 'virtual_host_finder';
UPDATE presets SET plugin_id = 'website-recon-2' WHERE plugin_id = 'website_recon';
UPDATE presets SET plugin_id = 'waf-detection' WHERE plugin_id = 'waf_detector';

-- 7. Revert plugins in plugins table
UPDATE plugins SET id = 'domain-finder' WHERE id = 'domain_finder';
UPDATE plugins SET id = 'google-dorking' WHERE id = 'google_dorking';
UPDATE plugins SET id = 'people-email-discovery' WHERE id = 'people_email_discovery';
UPDATE plugins SET id = 'port-scanner' WHERE id = 'port_scanner';
UPDATE plugins SET id = 'subdomain-finder' WHERE id = 'subdomain_finder';
UPDATE plugins SET id = 'url-fuzzer-2' WHERE id = 'url_fuzzer';
UPDATE plugins SET id = 'virtual-host-finder' WHERE id = 'virtual_host_finder';
UPDATE plugins SET id = 'website-recon-2' WHERE id = 'website_recon';
INSERT OR REPLACE INTO plugins (id, name, version, category, metadata_json) VALUES ('waf-detection', 'WAF Detector', '1.0.0', 'robots', '{}');

-- 8. Decrement the schema version if necessary in schema_migrations
-- DELETE FROM schema_migrations WHERE version = 7;
```
