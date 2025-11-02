"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from phoebe_server.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "service" in response.json()
