# Plugin Field Validation

This document describes the validation contract for plugin field metadata in SecuScan.

Plugin authors define fields in their plugin's schema. Each field can have an optional `validation` object that controls how the frontend form validates user input before a scan is started.

---

## Supported validation keys

| Key               | Type     | Description                                                  |
|-------------------|----------|--------------------------------------------------------------|
| `pattern`         | `string` | A regex string the trimmed value must match                  |
| `message`         | `string` | Custom error message shown when validation fails             |
| `min`             | `number` | Minimum value (integer fields only)                          |
| `max`             | `number` | Maximum value (integer fields only)                          |
| `validation_type` | `string` | Named preset — see table below. Takes priority over `pattern`|

---

## Named `validation_type` presets

Use these for common cases instead of writing your own regex:

| `validation_type` | Accepts                                  | Example               |
|-------------------|------------------------------------------|-----------------------|
| `url`             | HTTP or HTTPS URLs                       | `https://example.com` |
| `hostname`        | Hostnames with optional subdomains       | `sub.example.com`     |
| `domain`          | Domain names without a scheme            | `example.com`         |
| `ipv4`            | IPv4 addresses (0–255 per octet)         | `192.168.1.1`         |
| `port`            | Integer port numbers (1–65535)           | `8080`                |
| `cidr`            | IPv4 CIDR notation                       | `192.168.1.0/24`      |

If both `validation_type` and `pattern` are set, `validation_type` takes priority.

---

## Examples

### URL field

```json
{
  "id": "target_url",
  "label": "Target URL",
  "type": "string",
  "required": true,
  "placeholder": "https://example.com",
  "help": "Full URL of the target including scheme.",
  "validation": {
    "validation_type": "url",
    "message": "Enter a valid URL starting with http:// or https://"
  }
}
```

### Hostname field

```json
{
  "id": "target_host",
  "label": "Target Hostname",
  "type": "string",
  "required": true,
  "placeholder": "example.com",
  "help": "Hostname or subdomain to scan. Do not include http://.",
  "validation": {
    "validation_type": "hostname"
  }
}
```

### IPv4 field

```json
{
  "id": "target_ip",
  "label": "Target IP",
  "type": "string",
  "required": true,
  "placeholder": "192.168.1.1",
  "validation": {
    "validation_type": "ipv4",
    "message": "Enter a valid IPv4 address"
  }
}
```

### Port field (integer with range)

```json
{
  "id": "port",
  "label": "Port",
  "type": "integer",
  "required": false,
  "placeholder": "80",
  "validation": {
    "min": 1,
    "max": 65535,
    "message": "Port must be between 1 and 65535"
  }
}
```

### CIDR block field

```json
{
  "id": "subnet",
  "label": "Target Subnet",
  "type": "string",
  "required": false,
  "placeholder": "192.168.1.0/24",
  "validation": {
    "validation_type": "cidr"
  }
}
```

### Custom regex (backwards compatible)

Existing plugins using a raw `pattern` continue to work without changes:

```json
{
  "id": "api_key",
  "label": "API Key",
  "type": "string",
  "required": true,
  "validation": {
    "pattern": "^[A-Za-z0-9]{32,64}$",
    "message": "API key must be 32–64 alphanumeric characters"
  }
}
```

---

## Frontend behaviour

- **Required fields**: show an error if the value is empty, null, or whitespace.
- **Pattern / validation_type**: checked on non-empty string values only — an empty optional field is never flagged.
- **Integer min/max**: checked when the field has type `integer` and a value has been entered.
- **aria-invalid**: set to `true` on the input element when a validation error is present.
- **Inline error message**: shown directly below the field with `role="alert"`.
- **Scan button**: disabled while any field has a validation error.

---

## Backwards compatibility

Plugins that already define `validation.pattern` (without `validation_type`) continue to work exactly as before. No migration is required.

---

## Common Validation Mistakes & Troubleshooting Matrix

When writing or updating plugin schemas, authors frequently run into predictable validation edge cases. Use this matrix to identify and resolve common schema parsing issues.

### Troubleshooting Matrix

| Issue Symptoms | Root Cause | How to Fix |
| :--- | :--- | :--- |
| **`pattern` regex is being completely ignored** by the frontend form validation loop. | Both `validation_type` and `pattern` are defined in the object. `validation_type` takes strict structural priority over custom regex patterns. | Remove the `validation_type` key if you require custom regex behavior, or adapt your constraint to use an existing preset. |
| **`min` or `max` rules have no effect**; users can input any number they want. | The parent field configuration specifies `"type": "string"`. Range limits only evaluate when `"type": "integer"`. | Update the field configuration line to explicitly use `"type": "integer"`. |
| **Frontend crashes or hangs** when attempting to evaluate a custom input pattern. | The regex string defined inside `pattern` contains an unescaped or invalid syntax constraint. | Validate your regex block independently. Remember that JSON strings require backslashes to be double-escaped (e.g., use `\\d` instead of `\d`). |
| **An optional input field blocks form submission** even when left entirely blank by the user. | The field schema definition contains `"required": true`, overriding the empty string exception check. | Set `"required": false` so the validation engine skips evaluation on blank strings or null elements. |

### Rule Evaluation Reference

To keep schemas stable, the validation engine processes properties using this explicit order of execution:
```mermaid
graph TD
    A[User Input] --> B{Is field blank?}
    B -- Yes --> C{Is field 'required'? : true}
    C -- Yes --> D[Blocks Form Submission]
    C -- No --> E[Skip Checks: Valid]
    B -- No --> F{Has 'validation_type'?}
    F -- Yes --> G[Run Named Preset Rules<br>Ignores 'pattern']
    F -- No --> H[Run Custom 'pattern' Regex]