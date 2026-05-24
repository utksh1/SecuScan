import pytest
import asyncio
import uuid
import json
from backend.secuscan.database import get_db, init_db
from backend.secuscan.executor import executor
from backend.secuscan.models import TaskStatus

@pytest.mark.asyncio
async def test_database_schema_assets(setup_test_environment):
    """Verify that assets and relationship tables are created correctly in the database schema."""
    db = await init_db(f"{setup_test_environment}/test_secuscan.db")

    # Check if tables exist
    tables = await db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = {t["name"] for t in tables}

    assert "assets" in table_names
    assert "asset_findings" in table_names
    assert "asset_tasks" in table_names
    assert "asset_reports" in table_names

    await db.disconnect()

@pytest.mark.asyncio
async def test_asset_deduplication_and_relationships(setup_test_environment):
    """Test that host assets are deduplicated and linked to tasks and reports correctly."""
    db = await init_db(f"{setup_test_environment}/test_secuscan.db")

    # 1. Create a dummy task
    task_id1 = "task:test1"
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, status, inputs_json)
        VALUES (?, 'nmap', 'Nmap', 'http://192.168.1.5:8080/path', 'completed', '{}')
        """,
        (task_id1,)
    )

    # Create findings
    finding_id1 = "finding:1"
    await db.execute(
        """
        INSERT INTO findings (id, task_id, plugin_id, title, category, severity, target, description, metadata_json)
        VALUES (?, ?, 'nmap', 'Open Port: 8080/tcp', 'Network Service', 'low', '192.168.1.5', 'Port 8080 open', '{"port": 8080, "protocol": "tcp"}')
        """,
        (finding_id1, task_id1)
    )

    # Run updater
    await executor._update_assets_for_task(db, task_id1)

    # Check that host asset was created with normalized name
    host_assets = await db.fetchall("SELECT * FROM assets WHERE type='host'")
    assert len(host_assets) == 1
    assert host_assets[0]["name"] == "192.168.1.5"
    host_id = host_assets[0]["id"]

    # Check service asset was created under host
    service_assets = await db.fetchall("SELECT * FROM assets WHERE type='service'")
    assert len(service_assets) == 1
    assert service_assets[0]["name"] == "8080/tcp"
    assert service_assets[0]["host_id"] == host_id
    service_id = service_assets[0]["id"]

    # Check relationships
    task_links = await db.fetchall("SELECT * FROM asset_tasks")
    assert len(task_links) == 2  # one for host, one for service

    finding_links = await db.fetchall("SELECT * FROM asset_findings")
    assert len(finding_links) == 1
    assert finding_links[0]["asset_id"] == service_id
    assert finding_links[0]["finding_id"] == finding_id1

    # 2. Run a second task on the SAME target to verify deduplication
    task_id2 = "task:test2"
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, status, inputs_json)
        VALUES (?, 'nmap', 'Nmap', '192.168.1.5', 'completed', '{}')
        """,
        (task_id2,)
    )

    # Run updater
    await executor._update_assets_for_task(db, task_id2)

    # Verify no duplicate host asset was created
    all_hosts = await db.fetchall("SELECT * FROM assets WHERE type='host'")
    assert len(all_hosts) == 1

    await db.disconnect()

def test_assets_rest_endpoints(test_client):
    """Test standard REST API endpoints for assets using test client."""
    # Insert dummy data through sqlite connection directly (using the initialized test_client db)
    async def insert_data():
        db = await get_db()
        # Task
        await db.execute(
            "INSERT INTO tasks (id, plugin_id, tool_name, target, status) VALUES ('task:test', 'subfinder', 'Subfinder', 'example.com', 'completed')"
        )
        # Findings
        await db.execute(
            """
            INSERT INTO findings (id, task_id, plugin_id, title, category, severity, target, description, metadata_json)
            VALUES ('finding:sub', 'task:test', 'subfinder', 'Subdomain Found', 'Asset Discovery', 'info', 'example.com', 'Subdomain discovered', '{"subdomain": "api.example.com"}')
            """
        )
        await executor._update_assets_for_task(db, 'task:test')

    asyncio.run(insert_data())

    # Test GET /api/v1/assets
    response = test_client.get("/api/v1/assets")
    assert response.status_code == 200
    data = response.json()
    assert "assets" in data
    # We should have "example.com" (host) and "api.example.com" (subdomain host)
    names = {a["name"] for a in data["assets"]}
    assert "example.com" in names
    assert "api.example.com" in names

    # Test GET /api/v1/assets/graph
    response_graph = test_client.get("/api/v1/assets/graph")
    assert response_graph.status_code == 200
    graph = response_graph.json()
    assert "nodes" in graph
    assert "links" in graph
    node_labels = {n["label"] for n in graph["nodes"]}
    assert "example.com" in node_labels
    assert "api.example.com" in node_labels
    assert "Subdomain Found" in node_labels

    # Find an asset ID
    asset_id = next(a["id"] for a in data["assets"] if a["name"] == "example.com")

    # Test GET /api/v1/asset/{id}
    response_details = test_client.get(f"/api/v1/asset/{asset_id}")
    assert response_details.status_code == 200
    details = response_details.json()
    assert details["name"] == "example.com"
    assert "tasks" in details
    assert "findings" in details

    # Test GET /api/v1/finding/{id} to verify asset links nested inside finding details
    response_finding = test_client.get("/api/v1/finding/finding:sub")
    assert response_finding.status_code == 200
    f_details = response_finding.json()
    assert "assets" in f_details
    assert len(f_details["assets"]) > 0

def test_negative_cases(test_client):
    """Verify negative boundaries like fetching non-existent asset details or parameter injections."""
    # 1. Fetch non-existent asset ID -> should return 404
    response = test_client.get("/api/v1/asset/asset:host:nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Asset not found"

    # 2. Fetch non-existent finding details -> should return 404
    response = test_client.get("/api/v1/finding/finding:nonexistent")
    assert response.status_code == 404
