import re
from pathlib import Path
from backend.secuscan.main import app

# Map of TS Interface names to OpenAPI Schema names
TS_TO_OPENAPI_MAP = {
    "HealthResponse": "HealthResponse",
    "TaskResponse": "TaskResponse",
    "TaskStatusResponse": "TaskStatusResponse",
    "TaskPagination": "TaskPagination",
    "TasksResponse": "TasksResponse",
    "Finding": "Finding",
    "TaskResult": "TaskResult",
    "ScanActivity": "ScanActivity",
    "DashboardSummaryResponse": "DashboardSummaryResponse",
    "FindingsResponse": "FindingsResponse",
    "FindingAssetRef": "FindingAssetRef",
    "FindingDetailsResponse": "FindingDetailsResponse",
    "ReportItem": "ReportItem",
    "ReportsResponse": "ReportsResponse",
    "AssetResponseItem": "AssetResponseItem",
    "AssetsResponse": "AssetsResponse",
    "GraphNode": "GraphNode",
    "GraphLink": "GraphLink",
    "GraphResponse": "GraphResponse",
    "AssetDetailsResponse": "AssetDetailsResponse",
    "WorkflowStep": "WorkflowStep",
    "Workflow": "Workflow",
    "WorkflowRunResponse": "WorkflowRunResponse",
    "WorkflowDeleteResponse": "WorkflowDeleteResponse",
    "WorkflowsResponse": "WorkflowsResponse",
}

# Extra checks for OpenAPI schemas that map to the same TS interface
EXTRA_OPENAPI_SCHEMA_CHECKS = {
    "Workflow": ["WorkflowCreateResponse", "WorkflowUpdateResponse"],
}

def parse_ts_interfaces(ts_content: str):
    # Regex to capture interface declarations: export interface Name [extends Parent] { ... }
    interface_pattern = re.compile(
        r'export\s+interface\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{([^}]+)\}',
        re.MULTILINE
    )

    interfaces = {}
    for match in interface_pattern.finditer(ts_content):
        name = match.group(1)
        extends_name = match.group(2)
        body = match.group(3)

        fields = {}
        for line in body.split('\n'):
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('/*') or line.startswith('*'):
                continue

            # Matches: fieldName?: type; or fieldName: type;
            field_match = re.match(r'^(\w+)(\?)?\s*:\s*([^;]+);?$', line)
            if field_match:
                field_name = field_match.group(1)
                optional = bool(field_match.group(2))
                field_type = field_match.group(3).strip()
                fields[field_name] = {
                    "optional": optional,
                    "type": field_type
                }

        interfaces[name] = {
            "extends": extends_name,
            "fields": fields
        }

    # Resolve extends inheritance
    resolved_interfaces = {}
    for name, data in interfaces.items():
        fields = dict(data["fields"])
        parent = data["extends"]
        visited = set()
        while parent:
            if parent in visited:
                break
            visited.add(parent)
            if parent in interfaces:
                for p_field, p_data in interfaces[parent]["fields"].items():
                    if p_field not in fields:
                        fields[p_field] = p_data
                parent = interfaces[parent]["extends"]
            else:
                break
        resolved_interfaces[name] = fields

    return resolved_interfaces


def check_type_match(ts_type: str, schema: dict, schemas: dict, path: str):
    # Strip null/undefined union parts from TS type
    parts = [t.strip() for t in ts_type.split("|")]
    clean_parts = [p for p in parts if p not in ["null", "undefined"]]
    if not clean_parts:
        return
    clean_ts_type = clean_parts[0]

    # Resolve ref
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        schema = schemas.get(ref_name, {})

    # Resolve anyOf / oneOf
    if "anyOf" in schema:
        non_null_schemas = [s for s in schema["anyOf"] if s.get("type") != "null"]
        if non_null_schemas:
            schema = non_null_schemas[0]
        else:
            schema = schema["anyOf"][0]
    elif "oneOf" in schema:
        non_null_schemas = [s for s in schema["oneOf"] if s.get("type") != "null"]
        if non_null_schemas:
            schema = non_null_schemas[0]
        else:
            schema = schema["oneOf"][0]

    # Resolve ref inside resolved schemas
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        schema = schemas.get(ref_name, {})

    schema_types = schema.get("type", "any")

    if isinstance(schema_types, list):
        schema_type = [t for t in schema_types if t != "null"][0] if [t for t in schema_types if t != "null"] else "any"
    else:
        schema_type = schema_types

    # Resolve array types
    if clean_ts_type.endswith("[]"):
        item_ts_type = clean_ts_type[:-2]
        if schema_type != "array":
            raise AssertionError(f"{path}: TS expects array, but OpenAPI type is '{schema_type}'")
        items_schema = schema.get("items", {})
        check_type_match(item_ts_type, items_schema, schemas, f"{path}[]")
        return

    # Resolve literal unions (e.g. 'queued' | 'running')
    if len(clean_parts) > 1 and all(p.startswith(("'", '"')) and p.endswith(("'", '"')) for p in clean_parts):
        literals = [p.strip("'\"") for p in clean_parts]
        if schema_type != "string":
            raise AssertionError(f"{path}: TS literal union expects string type in OpenAPI, got '{schema_type}'")
        schema_enum = schema.get("enum", [])
        for lit in literals:
            if lit not in schema_enum:
                raise AssertionError(f"{path}: TS enum value '{lit}' not in OpenAPI enum values: {schema_enum}")
        return

    # Check primitive type matches
    if clean_ts_type == "string":
        if schema_type != "string":
            raise AssertionError(f"{path}: TS type is string, but OpenAPI type is '{schema_type}'")
    elif clean_ts_type == "number":
        if schema_type not in ["integer", "number"]:
            raise AssertionError(f"{path}: TS type is number, but OpenAPI type is '{schema_type}'")
    elif clean_ts_type == "boolean":
        if schema_type != "boolean":
            raise AssertionError(f"{path}: TS type is boolean, but OpenAPI type is '{schema_type}'")
    elif clean_ts_type in ["any", "unknown", "object"] or clean_ts_type.startswith("Record<"):
        # Matches any type or object
        pass
    else:
        # Reference type check
        expected_ref = TS_TO_OPENAPI_MAP.get(clean_ts_type, clean_ts_type)
        if "$ref" in schema:
            ref_name = schema["$ref"].split("/")[-1]
            if ref_name != expected_ref:
                raise AssertionError(f"{path}: TS expects reference to '{clean_ts_type}' (mapped to '{expected_ref}'), but OpenAPI references '{ref_name}'")
        elif schema_type == "object" or schema_type == "any":
            pass
        else:
            # Check if ref is in schemas
            if expected_ref not in schemas:
                raise AssertionError(f"{path}: TS references custom interface '{clean_ts_type}' not found in OpenAPI components/schemas")


def verify_interface_schema_match(ts_name: str, ts_fields: dict, schema: dict, schemas: dict):
    schema_properties = schema.get("properties", {})
    schema_required = schema.get("required", [])

    # Verify that all properties in OpenAPI schema exist in TS interface
    for prop_name, prop_schema in schema_properties.items():
        path = f"{ts_name}.{prop_name}"
        # Check if property is in TS
        if prop_name not in ts_fields:
            if prop_name in schema_required:
                raise AssertionError(f"Required OpenAPI property '{prop_name}' in schema is missing in TS interface '{ts_name}'")
            continue

        ts_field = ts_fields[prop_name]

        # Check optionality matching
        if prop_name in schema_required and ts_field["optional"]:
            raise AssertionError(f"{path}: Property is required in OpenAPI, but optional ('?') in TS")

        # Verify type matching
        check_type_match(ts_field["type"], prop_schema, schemas, path)

    # Verify that any non-optional property present in TS also exists in the OpenAPI schema properties
    for field_name, field_data in ts_fields.items():
        if field_name not in schema_properties and not field_data["optional"]:
            raise AssertionError(f"Non-optional TS property '{field_name}' in '{ts_name}' does not exist in OpenAPI schema properties")


def test_api_contract_drift():
    """Verify that TypeScript client interfaces in api.ts match backend Pydantic models."""
    # Find api.ts path relative to this test file
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    api_ts_path = repo_root / "frontend" / "src" / "api.ts"

    assert api_ts_path.exists(), f"Could not find api.ts at {api_ts_path}"

    with open(api_ts_path, "r", encoding="utf-8") as f:
        ts_content = f.read()

    ts_interfaces = parse_ts_interfaces(ts_content)
    openapi = app.openapi()
    openapi_schemas = openapi.get("components", {}).get("schemas", {})

    # Verify that each mapped interface matches
    for ts_name, openapi_name in TS_TO_OPENAPI_MAP.items():
        assert ts_name in ts_interfaces, f"TS interface '{ts_name}' missing from api.ts"
        assert openapi_name in openapi_schemas, f"OpenAPI schema '{openapi_name}' missing from backend"

        ts_fields = ts_interfaces[ts_name]
        schema = openapi_schemas[openapi_name]
        verify_interface_schema_match(ts_name, ts_fields, schema, openapi_schemas)

    # Extra checks for schemas mapped to the same TS interface
    for ts_name, extra_openapi_names in EXTRA_OPENAPI_SCHEMA_CHECKS.items():
        ts_fields = ts_interfaces[ts_name]
        for openapi_name in extra_openapi_names:
            assert openapi_name in openapi_schemas, f"OpenAPI schema '{openapi_name}' missing from backend"
            schema = openapi_schemas[openapi_name]
            verify_interface_schema_match(ts_name, ts_fields, schema, openapi_schemas)
