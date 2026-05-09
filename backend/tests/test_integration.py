import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app


@pytest.fixture(scope="module")
def client():
	"""Create a single TestClient instance for all tests."""
	with TestClient(app=app, raise_server_exceptions=False) as client:
		yield client


def test_health(client):
	"""Test that the API docs endpoint is accessible."""
	response = client.get("/docs")
	assert response.status_code == 200


def test_session_crud(client):
	"""Test basic session CRUD operations (create, read, update)."""
	# Create
	response = client.post("/api/sessions", json={"title": "Test"})
	assert response.status_code == 200
	session_id = response.json()["id"]
	assert len(session_id) > 0

	# Read
	response = client.get(f"/api/sessions/{session_id}")
	assert response.status_code == 200
	assert response.json()["id"] == session_id

	# Update
	response = client.put(f"/api/sessions/{session_id}", json={"title": "Updated"})
	assert response.status_code == 200
	assert response.json()["title"] == "Updated"


def test_list_sessions(client):
	"""Test that sessions list endpoint works."""
	response = client.get("/api/sessions")
	assert response.status_code == 200
	assert isinstance(response.json(), list)


def test_create_and_list_sessions(client):
	"""Test creating multiple sessions and listing them."""
	# Create a few sessions
	session_ids = []
	for i in range(3):
		response = client.post("/api/sessions", json={"title": f"Test Session {i}"})
		if response.status_code == 200:
			session_ids.append(response.json()["id"])

	# List sessions
	response = client.get("/api/sessions")
	assert response.status_code == 200
	sessions = response.json()
	assert isinstance(sessions, list)
	assert len(sessions) >= 3

	# Verify our created sessions are in the list
	session_titles = [s["title"] for s in sessions]
	for i in range(3):
		assert f"Test Session {i}" in session_titles


def test_session_not_found(client):
	"""Test that getting a non-existent session returns 404."""
	response = client.get("/api/sessions/nonexistent-id")
	assert response.status_code == 404


def test_create_session_without_title(client):
	"""Test creating a session without providing a title."""
	response = client.post("/api/sessions", json={})
	assert response.status_code == 200
	data = response.json()
	assert "title" in data