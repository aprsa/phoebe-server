"""Test database integration with session lifecycle."""

import time
import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from phoebe_server.main import app
from phoebe_server.manager import session_manager
from phoebe_server.config import config


@pytest.fixture(scope="module")
def client():
    """Create a test client with proper initialization."""
    # Initialize port pool and database (normally done in lifespan)
    session_manager.load_port_config()
    with TestClient(app) as test_client:
        yield test_client


def test_database_exists():
    """Test that database is initialized."""
    db_path = Path(config.database.path)
    assert db_path.exists(), f"Database not found at {db_path}"


def test_session_lifecycle_logging(client):
    """Test full session lifecycle is logged to database."""
    # Create a session
    response = client.post(
        "/dash/start-session",
        headers={"User-Agent": "pytest/1.0"}
    )
    assert response.status_code == 200
    session_data = response.json()
    client_id = session_data["client_id"]

    # Update user info
    response = client.post(
        f"/dash/update-user-info/{client_id}",
        json={"first_name": "Test", "last_name": "User"}
    )
    assert response.status_code == 200

    time.sleep(0.5)  # Allow DB writes to complete

    conn = sqlite3.connect(config.database.path)
    cursor = conn.cursor()

    try:
        # Check session record
        cursor.execute("""
            SELECT session_id, port, client_ip, user_agent, status
            FROM sessions WHERE session_id = ?
        """, (client_id,))
        session_row = cursor.fetchone()
        assert session_row is not None, "Session not found in database"
        assert session_row[0] == client_id
        assert session_row[1] == session_data["port"]
        assert session_row[2] is not None  # client_ip
        assert session_row[3] == "pytest/1.0"
        assert session_row[4] == "active"

        # Check user info
        cursor.execute("""
            SELECT first_name, last_name FROM session_user_info WHERE session_id = ?
        """, (client_id,))
        user_row = cursor.fetchone()
        assert user_row is not None
        assert user_row[0] == "Test"
        assert user_row[1] == "User"

        # Send ping command (should be filtered)
        response = client.post(
            f"/send/{client_id}",
            json={"command": "ping"}
        )
        assert response.status_code == 200

        # Send get_value command (should be logged)
        response = client.post(
            f"/send/{client_id}",
            json={"command": "get_value", "twig": "period@binary"}
        )
        assert response.status_code == 200

        time.sleep(0.5)  # Allow DB writes to complete

        # Check command log - ping should be filtered out
        cursor.execute("""
            SELECT command_name, success, execution_time_ms
            FROM session_commands WHERE session_id = ?
        """, (client_id,))
        commands = cursor.fetchall()
        assert len(commands) == 1, "Expected 1 logged command (ping filtered)"
        assert commands[0][0] == "get_value"
        assert commands[0][1] == 1  # success=True stored as 1
        assert commands[0][2] > 0  # execution time > 0

        # Check metrics - should have 2 (one per command)
        cursor.execute("""
            SELECT memory_used_mb FROM session_metrics WHERE session_id = ?
        """, (client_id,))
        metrics = cursor.fetchall()
        assert len(metrics) == 2, "Expected 2 memory metrics"
        assert all(m[0] > 0 for m in metrics), "Memory values should be positive"

        # End session
        response = client.post(f"/dash/end-session/{client_id}")
        assert response.status_code == 200

        time.sleep(0.5)  # Allow DB writes to complete

        # Check final session state
        cursor.execute("""
            SELECT status, termination_reason, destroyed_at
            FROM sessions WHERE session_id = ?
        """, (client_id,))
        final = cursor.fetchone()
        assert final is not None
        assert final[0] == "terminated"
        assert final[1] == "manual"
        assert final[2] is not None  # destroyed_at timestamp

    finally:
        conn.close()


def test_command_filtering(client):
    """Test that command logging respects filter configuration."""
    # Create a session
    response = client.post("/dash/start-session")
    assert response.status_code == 200
    client_id = response.json()["client_id"]

    try:
        # Send multiple ping commands
        for _ in range(3):
            response = client.post(f"/send/{client_id}", json={"command": "ping"})
            assert response.status_code == 200

        time.sleep(0.5)

        # Verify no pings were logged
        conn = sqlite3.connect(config.database.path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM session_commands
            WHERE session_id = ? AND command_name = 'ping'
        """, (client_id,))
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 0, "Ping commands should be filtered out"

    finally:
        # Cleanup
        client.post(f"/dash/end-session/{client_id}")
