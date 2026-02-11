"""Tests for the operations dashboard (Phase 2)."""

import pytest
from fastapi.testclient import TestClient

# Import app and reset state so tests are isolated
from dashboard.app import app, reset_demo_state


@pytest.fixture(autouse=True)
def _reset_demo():
    reset_demo_state()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_health_degraded_until_rollback(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "degraded"

    client.post("/api/services/checkout/rollback", json={"to_version": "v1.4.1"})
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_services_list(client):
    r = client.get("/api/services")
    assert r.status_code == 200
    data = r.json()
    assert "services" in data
    ids = [s["id"] for s in data["services"]]
    assert "checkout" in ids
    assert "payments" in ids


def test_service_detail_and_rollback(client):
    r = client.get("/api/services/checkout")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "checkout"
    assert data["name"] == "Checkout"
    assert len(data["deployments"]) >= 2

    r = client.post("/api/services/checkout/rollback", json={"to_version": "v1.4.1"})
    assert r.status_code == 200
    assert r.json()["rolled_back_to"] == "v1.4.1"


def test_login_redirects_to_services(client):
    r = client.post(
        "/api/login", json={"username": "demo", "password": "demo"}, follow_redirects=False
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/services"


def test_pages_serve_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Demo login" in r.text
    r = client.get("/services")
    assert r.status_code == 200
    assert "Checkout" in r.text
    r = client.get("/services/checkout")
    assert r.status_code == 200
    assert "Deployments" in r.text
    assert "Rollback" in r.text
