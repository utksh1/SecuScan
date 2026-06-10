# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to Semantic Versioning.

## [Unreleased]

### Added

* Initial changelog created following the Keep a Changelog format.
* Added backend validator checks in `plugin_validator.py` to enforce that plugin IDs match `^[a-z][a-z0-9_]*$` and correspond to their folder name.
* Added SQL migration script `007_standardize_plugin_ids.sql` to update historical data referencing renamed or duplicate plugin IDs across tasks, findings, crawl runs, asset services, audit logs, presets, and active plugins tables.

### Changed

* Standardized all plugin IDs to `snake_case` (e.g., `domain_finder`, `google_dorking`, `people_email_discovery`, `port_scanner`, `subdomain_finder`, `url_fuzzer`, `virtual_host_finder`, `website_recon`).
* Updated unit and integration tests to reference the normalized plugin IDs.

### Deprecated

* None.

### Removed

* Removed the duplicate `waf-detection` plugin (merged references and migrated legacy data to the `waf_detector` plugin).

### Fixed

* None.

### Security

* None.
