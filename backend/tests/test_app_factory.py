from fastapi import FastAPI


def test_create_app_builds_fastapi_app_with_api_routes():
	from app import create_app

	app = create_app()

	assert isinstance(app, FastAPI)
	paths = {route.path for route in app.routes}
	assert "/api/sessions" in paths
	assert "/api/agui" in paths


def test_global_app_remains_available():
	from app import app

	assert isinstance(app, FastAPI)
