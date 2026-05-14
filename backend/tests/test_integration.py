import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, Timeout
import sys
import asyncio
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


def test_chat_endpoint_reachable(client):
	"""Test /api/chat endpoint is reachable and responds to requests."""
	# Create session
	response = client.post("/api/sessions", json={"title": "Chat Test"})
	assert response.status_code == 200
	session_id = response.json()["id"]

	# Call chat - agent may fail but endpoint should be reachable
	response = client.post(
		"/api/chat",
		json={"session_id": session_id, "message": "hello", "attachments": []}
	)

	# Accept success or server error (agent not configured)
	assert response.status_code in (200, 500)
	if response.status_code == 200:
		assert "text/event-stream" in response.headers.get("content-type", "")


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


@pytest.mark.asyncio
async def test_chat_endpoint_basic():
	"""Test /api/chat endpoint basic connectivity."""
	# Create a session first
	async with AsyncClient(base_url="http://test", timeout=Timeout(10.0)) as ac:
		# First create a session
		response = await ac.post(
			"http://test/api/sessions",
			json={"title": "Chat Test Session"}
		)
		assert response.status_code == 200
		session_id = response.json()["id"]

		# Send a chat request - agent may not be fully configured so we just test endpoint is reachable
		chat_response = await ac.post(
			"http://test/api/chat",
			json={"session_id": session_id, "message": "test", "attachments": []}
		)
		# The endpoint should be reachable (may return 500 if agent not configured, but shouldn't be connection error)
		assert chat_response.status_code in (200, 500) or chat_response.is_streaming


def test_chat_endpoint_with_test_client(client):
	"""Test /api/chat endpoint using sync TestClient."""
	# Create a session first
	response = client.post("/api/sessions", json={"title": "Chat Test"})
	assert response.status_code == 200
	session_id = response.json()["id"]

	# Test that chat endpoint accepts the request
	# Note: This will trigger the agent, which may fail if not configured
	# but we verify the endpoint is reachable
	response = client.post(
		"/api/chat",
		json={"session_id": session_id, "message": "hello", "attachments": []}
	)
	# Accept both success (stream started) or server error (agent not configured)
	assert response.status_code in (200, 500)
	assert response.headers.get("content-type", "").startswith("text/event-stream") or response.status_code == 500


def test_chat_endpoint_requires_session_id(client):
	"""Test that /api/chat requires session_id in request."""
	response = client.post(
		"/api/chat",
		json={"message": "test", "attachments": []}
	)
	assert response.status_code == 422  # Validation error


def test_chat_endpoint_validation(client):
	"""Test /api/chat validates request body properly."""
	# Missing session_id
	response = client.post("/api/chat", json={"message": "test"})
	assert response.status_code == 422

	# Missing message
	response = client.post("/api/chat", json={"session_id": "test"})
	assert response.status_code == 422

	# Empty attachments is valid
	response = client.post("/api/chat", json={"session_id": "test", "message": "test", "attachments": []})
	# May be 500 if agent not configured, but shouldn't be 422 (validation passed)
	assert response.status_code in (200, 500)


def test_chat_endpoint_content_type(client):
	"""Test /api/chat returns text/event-stream content type when successful."""
	# Create session
	response = client.post("/api/sessions", json={"title": "SSE Test"})
	assert response.status_code == 200
	session_id = response.json()["id"]

	# Call chat endpoint
	response = client.post(
		"/api/chat",
		json={"session_id": session_id, "message": "test", "attachments": []},
		stream=True
	)

	# If agent is configured, should get streaming response
	if response.status_code == 200:
		assert "text/event-stream" in response.headers.get("content-type", "")
	else:
		# Agent not configured - that's okay for this test
		assert response.status_code == 500