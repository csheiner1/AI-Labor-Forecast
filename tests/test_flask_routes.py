"""Tests for Flask dashboard routes."""
import pytest
import json


@pytest.fixture
def client():
    """Create Flask test client."""
    from dashboard.app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        # Warm up data loading
        c.get("/")
        yield c


def test_index_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"AI Labor Displacement" in resp.data or b"Social Impact" in resp.data


def test_equity_200(client):
    resp = client.get("/equity")
    assert resp.status_code == 200
    assert b"Equity" in resp.data


def test_geographic_200(client):
    resp = client.get("/geographic")
    assert resp.status_code == 200
    assert b"Geographic" in resp.data


def test_political_200(client):
    resp = client.get("/political")
    assert resp.status_code == 200
    assert b"Political" in resp.data


def test_transitions_200(client):
    resp = client.get("/transitions")
    assert resp.status_code == 200
    assert b"Transition" in resp.data


def test_api_transition(client):
    """API should return JSON with source and targets."""
    resp = client.get("/api/transition/11-1011?n=5&max_displacement=0.15")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "source" in data
    assert "targets" in data
    assert data["source"]["soc"] == "11-1011"
    assert isinstance(data["targets"], list)


def test_api_transition_missing_soc(client):
    """API should handle missing SOC gracefully."""
    resp = client.get("/api/transition/99-9999?n=5")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["targets"] == []


def test_404_on_unknown_route(client):
    resp = client.get("/nonexistent")
    assert resp.status_code == 404
