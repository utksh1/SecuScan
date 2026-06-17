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

## Updating plugin checksums

When changing plugin metadata or parser behavior, refresh the stored checksum so metadata validation stays in sync.

Typical changes that require a checksum refresh include:

- Updating a plugin `metadata.json` file
- Changing parser expectations or capabilities
- Modifying plugin fields or defaults

After making changes, run:

```bash
python scripts/refresh_plugin_checksum.py --plugin <plugin_name>
```

Then verify that the `checksum` field inside the plugin metadata has been updated and commit the resulting change together with the documentation update.

This keeps parser and metadata expectations aligned and prevents checksum validation failures in CI.
