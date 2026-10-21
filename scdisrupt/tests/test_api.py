"""Integration tests for SC-Disrupt FastAPI REST API."""
import pytest
from fastapi.testclient import TestClient

from scdisrupt.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "scdisrupt"


def test_get_network(client):
    response = client.get("/network")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Global Sample Supply Chain"
    assert data["total_nodes"] > 0
    assert data["total_lanes"] > 0
    node_ids = [n["id"] for n in data["nodes"]]
    assert "SUP_1" in node_ids
    assert "WH_A" in node_ids


def test_simulate_cascade_endpoint(client):
    payload = {
        "disruption": {
            "disruption_type": "port_strike",
            "parameters": {"lead_time_multiplier": 2.5},
        },
        "runs": 2,
        "sim_days": 15,
        "seed": 42,
    }
    response = client.post("/simulate/cascade", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "disruption_name" in data
    assert "baseline_summary" in data
    assert "disrupted_summary" in data
    assert "service_level_delta" in data


def test_recover_endpoint(client):
    payload = {
        "disruption": {
            "disruption_type": "port_strike",
            "parameters": {"lead_time_multiplier": 2.5},
        },
        "runs": 2,
        "sim_days": 15,
        "seed": 42,
    }
    response = client.post("/recover", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "disruption_name" in data
    assert "plans" in data
    assert len(data["plans"]) >= 1
    assert "executive_briefing" in data
    assert "EXECUTIVE INCIDENT RESPONSE BRIEFING" in data["executive_briefing"]
    top_plan = data["plans"][0]
    assert "rank" in top_plan
    assert top_plan["rank"] == 1
    assert "actions" in top_plan
    assert len(top_plan["actions"]) > 0


def test_new_disruption_types_api(client):
    for dtype, params in [
        ("cyberattack", {"target_node_id": "FAC_1", "throughput_reduction": 0.5}),
        ("canal_blockage", {"lead_time_multiplier": 3.0, "cost_multiplier": 1.4}),
        ("raw_material_ban", {"supplier_ids": ["SUP_1"], "capacity_curtailment": 0.8}),
    ]:
        payload = {
            "disruption": {
                "disruption_type": dtype,
                "parameters": params,
            },
            "runs": 2,
            "sim_days": 10,
            "seed": 42,
        }
        res = client.post("/simulate/cascade", json=payload)
        assert res.status_code == 200, f"Failed for {dtype}: {res.text}"
        data = res.json()
        assert "disrupted_summary" in data

