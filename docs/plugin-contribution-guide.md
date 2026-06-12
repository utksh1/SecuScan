# Plugin Contribution & Testing Guide

This guide outlines the development workflow for adding new plugins or editing existing plugins in SecuScan. Following these steps ensures your plugin changes load correctly, pass schema validations, and satisfy automated tests.

---

## 1. Overview

SecuScan features a pluggable architecture. Plugins are self-contained scanner descriptions that define:
1. **Metadata (`metadata.json`)**: Schema fields, safety configuration, run engine types, and checksums.
2. **Parser (`parser.py`)**: (Optional) Python code to normalize raw CLI/Docker output into the structured findings format.

To maintain system integrity, the backend verifies plugin files before loading them. Any modifications to a plugin must be accompanied by a refreshed integrity checksum and valid schema properties.

---

## 2. Plugin Anatomy

Each plugin is located in its own subdirectory under `plugins/`. A standard plugin directory has the following structure:

```text
plugins/
  my_plugin/
    metadata.json    # Required: contains schema and CLI/Docker engine run arguments
    parser.py        # Required if output.parser is "custom": parses stdout to JSON
```

### Required metadata.json Fields
A minimal, valid `metadata.json` has the following shape:

```json
{
  "id": "my_plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "description": "What this plugin does.",
  "category": "recon",
  "icon": "🔍",
  "engine": {
    "type": "cli",
    "binary": "mytool"
  },
  "command_template": ["mytool", "{target}"],
  "fields": [
    {
      "id": "target",
      "label": "Target Host",
      "type": "string",
      "required": true
    }
  ],
  "output": {
    "parser": "text"
  },
  "safety": {
    "level": "safe",
    "requires_consent": false
  },
  "checksum": "d131dd02c5e6eec4693d9a0698bc92ee2c2d8471ff0f8ef612c6a0c4e7c99b82"
}
```

> [!IMPORTANT]
> The `checksum` field in `metadata.json` secures the integrity of the plugin definition. You should **never manually edit this field**. It is calculated and populated using helper scripts.

For detailed documentation on field types, options, validation keys, and custom pattern presets, see [docs/plugin-validation.md](plugin-validation.md).

---

## 3. Editing an Existing Plugin

If you need to update a plugin's settings, arguments, or parsing behavior, use the following linear workflow:

### Step 3a: Edit Files
Edit `plugins/<plugin_id>/metadata.json` or `plugins/<plugin_id>/parser.py` as needed.

### Step 3b: Refresh the Checksum
Any change to `metadata.json` or `parser.py` invalidates the plugin's checksum. The backend will reject the plugin on startup if its checksum does not match its contents, causing unrelated backend tests to fail.

Run the refresh helper to calculate and save the new checksum:
```bash
python scripts/refresh_plugin_checksum.py --plugin <plugin_id>
```

### Step 3c: Validate the Plugin
Ensure that your changes follow the metadata rules and schema definitions:
```bash
python scripts/validate_plugin.py --plugin <plugin_id>
```

### Step 3d: Run the Test Suite
Verify everything is working correctly by running the backend pytest suite:
```bash
# Run all tests
./testing/test_python.sh

# Or target plugin tests specifically for fast feedback:
python -m pytest testing/backend/unit/test_plugin_integrity.py
python -m pytest testing/backend/integration/test_parser_output_contract.py
```

### Step 3e: Commit Changes
Ensure you commit both the source modifications and the updated `metadata.json` (containing the new checksum) **in the same commit**.

---

## 4. Checksum Helper Reference

The checksum utility `scripts/refresh_plugin_checksum.py` provides several arguments for managing plugin integrity:

* **Refresh a single plugin:**
  ```bash
  python scripts/refresh_plugin_checksum.py --plugin <plugin-id>
  ```
* **Refresh all plugins at once:**
  ```bash
  python scripts/refresh_plugin_checksum.py --all
  ```
* **Preview updates (Dry Run):**
  Check which plugins are out of date without changing any files:
  ```bash
  python scripts/refresh_plugin_checksum.py --all --dry-run
  ```
  If dry run reports `[UPDATE]` for any plugin, you must run the script without `--dry-run` before committing.

---

## 5. Adding a New Plugin

Follow this procedure when contributing a new scanner or tool integration:

### Step 5a: Create Directory and Files
Create a new folder under `plugins/` with a unique, lowercase snake_case ID (e.g. `plugins/my_scanner/`). Inside, add:
* `metadata.json`
* `parser.py` (if using `output.parser = "custom"`)

### Step 5b: Parser Contract (`parse()`)
If your plugin parses tool outputs into structured findings, set `"parser": "custom"` under `"output"` in `metadata.json`.

Your `parser.py` must export a callable `parse(output: str) -> dict` function that implements the parser contract:
* It accepts a single `str` argument containing the raw standard output of the tool.
* It returns a dictionary.
* The returned dictionary must contain the following keys:
  * `count` (`int`): The number of findings detected.
  * `findings` (`list` of `dict`): Individual finding descriptions. Each finding dictionary can optionally define `title`, `description`, `severity` (e.g., `info`, `low`, `medium`, `high`, `critical`), and `metadata`.
  * `summary` (`list` of `str`): A list of text lines summarizing the scan outcomes.

If a plugin output is raw text and does not require structured dissection, set `"parser": "text"` instead. The backend handles pass-through parsing automatically and no `parser.py` is needed.

### Step 5c: Generate Initial Checksum
To generate the first checksum, add a dummy `"checksum": ""` string in your `metadata.json` and execute:
```bash
python scripts/refresh_plugin_checksum.py --plugin <your_plugin_id>
```

### Step 5d: Register & Validate
Add your new plugin details to the index in [PLUGINS.md](../PLUGINS.md). Then validate and test it.

---

## 6. Fixture-Based Parser Tests

### What "Fixture-Based" Means
Parser unit tests in SecuScan are hermetic and decoupled from the actual binaries. Instead of invoking CLI commands or launching Docker containers, parser tests pass pre-recorded string outputs (fixtures) straight into the `parse()` function.

This design makes testing extremely fast, reproducible, and runnable in a basic CI/CD runner without installing any security scanners or tool binaries.

### Writing a New Parser Test
When adding or updating a custom parser, write a corresponding unit test file: `testing/backend/unit/test_<plugin_id>_parser.py`.

Follow the inline-fixture pattern used in [test_dns_enum_parser.py](../testing/backend/unit/test_dns_enum_parser.py):
1. **Import the parse function:**
   ```python
   from plugins.my_plugin.parser import parse
   ```
2. **Define raw tool output:** Create a multiline string simulating actual tool output.
3. **Execute the parser:** Call `result = parse(raw_output)`.
4. **Assert details:** Assert on the dictionary keys, expected counts, and finding content.
5. **Handle edge cases:** Write a test asserting that empty input (`""`) or malformed/garbage input doesn't crash the parser.

### Core Validator Fixtures
Under [testing/backend/unit/fixtures/plugins/](../testing/backend/unit/fixtures/plugins/), you will find:
* `valid_plugin/`: Contains a schema-perfect `metadata.json` demonstrating required structures. Used by validator tests to prove valid layouts pass.
* `invalid_plugin/`: Deliberately violates rules (invalid safety level, missing name, duplicate field IDs, custom parser without a file). Used to assert validator error reporting.

> [!NOTE]
> Do not modify these core fixtures unless you are explicitly changing the parser validation or schema rules in the backend validator.

---

## 7. How the CI Validates Plugins

When you submit a PR, the CI runner verifies plugin health across three primary test suites:

| Test File | Verification Goal | Reason for Failure |
|---|---|---|
| [test_plugin_integrity.py](../testing/backend/unit/test_plugin_integrity.py) | Checks that checksums match and IDs/names are globally unique. | Outdated checksum, forgotten checksum generation, or duplicated plugin metadata ID/Name. |
| [test_plugin_validator.py](../testing/backend/unit/test_plugin_validator.py) | Asserts the validation rules correctly validate metadata rules against fixtures. | A regression in validation logic (rarely triggered by simple plugin edits). |
| [test_parser_output_contract.py](../testing/backend/integration/test_parser_output_contract.py) | Verifies custom parser imports and output compliance on empty and raw structures. | A custom parser does not export a callable `parse()` function, crashes on load, or returns a dictionary missing mandatory output keys. |

---

## 8. Checklist Before Opening a PR

Prior to committing and opening a Pull Request for a plugin change, run through this checklist:

- [ ] `metadata.json` declares all required fields.
- [ ] Any custom `parser.py` exports `parse(output: str) -> dict`.
- [ ] Checksum has been updated with `python scripts/refresh_plugin_checksum.py --plugin <id>`.
- [ ] Local validator exits cleanly: `python scripts/validate_plugin.py --plugin <id>`.
- [ ] A dedicated parser test file exists under `testing/backend/unit/test_<id>_parser.py` and covers happy/unhappy paths.
- [ ] All python backend tests pass: `./testing/test_python.sh`.
- [ ] The plugin index in [PLUGINS.md](../PLUGINS.md) has been updated (if adding a new plugin).
