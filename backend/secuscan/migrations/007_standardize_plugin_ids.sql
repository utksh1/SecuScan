-- Migration: 007_standardize_plugin_ids
-- Update references to non-conforming and duplicate plugin IDs across all database tables.

-- 1. Rename plugins in tasks table
UPDATE tasks SET plugin_id = 'domain_finder' WHERE plugin_id = 'domain-finder';
UPDATE tasks SET plugin_id = 'google_dorking' WHERE plugin_id = 'google-dorking';
UPDATE tasks SET plugin_id = 'people_email_discovery' WHERE plugin_id = 'people-email-discovery';
UPDATE tasks SET plugin_id = 'port_scanner' WHERE plugin_id = 'port-scanner';
UPDATE tasks SET plugin_id = 'subdomain_finder' WHERE plugin_id = 'subdomain-finder';
UPDATE tasks SET plugin_id = 'url_fuzzer' WHERE plugin_id = 'url-fuzzer-2';
UPDATE tasks SET plugin_id = 'virtual_host_finder' WHERE plugin_id = 'virtual-host-finder';
UPDATE tasks SET plugin_id = 'website_recon' WHERE plugin_id = 'website-recon-2';
UPDATE tasks SET plugin_id = 'waf_detector' WHERE plugin_id = 'waf-detection';

-- 2. Rename plugins in findings table
UPDATE findings SET plugin_id = 'domain_finder' WHERE plugin_id = 'domain-finder';
UPDATE findings SET plugin_id = 'google_dorking' WHERE plugin_id = 'google-dorking';
UPDATE findings SET plugin_id = 'people_email_discovery' WHERE plugin_id = 'people-email-discovery';
UPDATE findings SET plugin_id = 'port_scanner' WHERE plugin_id = 'port-scanner';
UPDATE findings SET plugin_id = 'subdomain_finder' WHERE plugin_id = 'subdomain-finder';
UPDATE findings SET plugin_id = 'url_fuzzer' WHERE plugin_id = 'url-fuzzer-2';
UPDATE findings SET plugin_id = 'virtual_host_finder' WHERE plugin_id = 'virtual-host-finder';
UPDATE findings SET plugin_id = 'website_recon' WHERE plugin_id = 'website-recon-2';
UPDATE findings SET plugin_id = 'waf_detector' WHERE plugin_id = 'waf-detection';

-- 3. Rename plugins in crawl_runs table
UPDATE crawl_runs SET plugin_id = 'domain_finder' WHERE plugin_id = 'domain-finder';
UPDATE crawl_runs SET plugin_id = 'google_dorking' WHERE plugin_id = 'google-dorking';
UPDATE crawl_runs SET plugin_id = 'people_email_discovery' WHERE plugin_id = 'people-email-discovery';
UPDATE crawl_runs SET plugin_id = 'port_scanner' WHERE plugin_id = 'port-scanner';
UPDATE crawl_runs SET plugin_id = 'subdomain_finder' WHERE plugin_id = 'subdomain-finder';
UPDATE crawl_runs SET plugin_id = 'url_fuzzer' WHERE plugin_id = 'url-fuzzer-2';
UPDATE crawl_runs SET plugin_id = 'virtual_host_finder' WHERE plugin_id = 'virtual-host-finder';
UPDATE crawl_runs SET plugin_id = 'website_recon' WHERE plugin_id = 'website-recon-2';
UPDATE crawl_runs SET plugin_id = 'waf_detector' WHERE plugin_id = 'waf-detection';

-- 4. Rename plugins in asset_services table
UPDATE asset_services SET plugin_id = 'domain_finder' WHERE plugin_id = 'domain-finder';
UPDATE asset_services SET plugin_id = 'google_dorking' WHERE plugin_id = 'google-dorking';
UPDATE asset_services SET plugin_id = 'people_email_discovery' WHERE plugin_id = 'people-email-discovery';
UPDATE asset_services SET plugin_id = 'port_scanner' WHERE plugin_id = 'port-scanner';
UPDATE asset_services SET plugin_id = 'subdomain_finder' WHERE plugin_id = 'subdomain-finder';
UPDATE asset_services SET plugin_id = 'url_fuzzer' WHERE plugin_id = 'url-fuzzer-2';
UPDATE asset_services SET plugin_id = 'virtual_host_finder' WHERE plugin_id = 'virtual-host-finder';
UPDATE asset_services SET plugin_id = 'website_recon' WHERE plugin_id = 'website-recon-2';
UPDATE asset_services SET plugin_id = 'waf_detector' WHERE plugin_id = 'waf-detection';

-- 5. Rename plugins in audit_log table
UPDATE audit_log SET plugin_id = 'domain_finder' WHERE plugin_id = 'domain-finder';
UPDATE audit_log SET plugin_id = 'google_dorking' WHERE plugin_id = 'google-dorking';
UPDATE audit_log SET plugin_id = 'people_email_discovery' WHERE plugin_id = 'people-email-discovery';
UPDATE audit_log SET plugin_id = 'port_scanner' WHERE plugin_id = 'port-scanner';
UPDATE audit_log SET plugin_id = 'subdomain_finder' WHERE plugin_id = 'subdomain-finder';
UPDATE audit_log SET plugin_id = 'url_fuzzer' WHERE plugin_id = 'url-fuzzer-2';
UPDATE audit_log SET plugin_id = 'virtual_host_finder' WHERE plugin_id = 'virtual-host-finder';
UPDATE audit_log SET plugin_id = 'website_recon' WHERE plugin_id = 'website-recon-2';
UPDATE audit_log SET plugin_id = 'waf_detector' WHERE plugin_id = 'waf-detection';

-- 6. Rename plugins in presets table
UPDATE presets SET plugin_id = 'domain_finder' WHERE plugin_id = 'domain-finder';
UPDATE presets SET plugin_id = 'google_dorking' WHERE plugin_id = 'google-dorking';
UPDATE presets SET plugin_id = 'people_email_discovery' WHERE plugin_id = 'people-email-discovery';
UPDATE presets SET plugin_id = 'port_scanner' WHERE plugin_id = 'port-scanner';
UPDATE presets SET plugin_id = 'subdomain_finder' WHERE plugin_id = 'subdomain-finder';
UPDATE presets SET plugin_id = 'url_fuzzer' WHERE plugin_id = 'url-fuzzer-2';
UPDATE presets SET plugin_id = 'virtual_host_finder' WHERE plugin_id = 'virtual-host-finder';
UPDATE presets SET plugin_id = 'website_recon' WHERE plugin_id = 'website-recon-2';
UPDATE presets SET plugin_id = 'waf_detector' WHERE plugin_id = 'waf-detection';

-- 7. Rename plugins in plugins table
UPDATE plugins SET id = 'domain_finder' WHERE id = 'domain-finder';
UPDATE plugins SET id = 'google_dorking' WHERE id = 'google-dorking';
UPDATE plugins SET id = 'people_email_discovery' WHERE id = 'people-email-discovery';
UPDATE plugins SET id = 'port_scanner' WHERE id = 'port-scanner';
UPDATE plugins SET id = 'subdomain_finder' WHERE id = 'subdomain-finder';
UPDATE plugins SET id = 'url_fuzzer' WHERE id = 'url-fuzzer-2';
UPDATE plugins SET id = 'virtual_host_finder' WHERE id = 'virtual-host-finder';
UPDATE plugins SET id = 'website_recon' WHERE id = 'website-recon-2';
DELETE FROM plugins WHERE id = 'waf-detection';
