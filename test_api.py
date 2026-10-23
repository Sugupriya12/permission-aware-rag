
import api
from fastapi.testclient import TestClient

client = TestClient(api.app)

ENGINEER_HEADERS = {
    "Authorization": "Bearer dev-token-engineer"
}
HR_HEADERS = {
    "Authorization": "Bearer dev-token-hr"
}


# Use a fake answer so API tests don't call Gemini repeatedly.
def fake_answer(query, documents):
    if not documents:
        return "No authorized documents found."
    return f"Test answer [{documents[0]['id']}]"


def setup_module():
    api.generate_answer = fake_answer


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_authorized_query():
    response = client.post(
        "/query",
        headers=ENGINEER_HEADERS,
        json={"query": "How do I deploy code?", "top_k": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "org-a"
    assert data["result_count"] > 0
    assert any(s["document_id"] == "doc-001" for s in data["sources"])
    assert data["answer"]


def test_missing_token_rejected():
    response = client.post("/query", json={"query": "deployment"})
    assert response.status_code == 401


def test_invalid_token_rejected():
    response = client.post(
        "/query",
        headers={"Authorization": "Bearer fake-token"},
        json={"query": "deployment"},
    )
    assert response.status_code == 401


def test_cannot_spoof_tenant_or_role():
    response = client.post(
        "/query",
        headers=ENGINEER_HEADERS,
        json={
            "query": "deployment",
            "tenant_id": "org-b",
            "user_role": "admin",
        },
    )
    assert response.status_code == 422


def test_role_restriction():
    response = client.post(
        "/query",
        headers=ENGINEER_HEADERS,
        json={"query": "How many annual leave days?"},
    )
    assert response.status_code == 200
    document_ids = [
        item["document_id"] for item in response.json()["sources"]
    ]
    assert "doc-002" not in document_ids


def test_authorized_hr_access():
    response = client.post(
        "/query",
        headers=HR_HEADERS,
        json={"query": "How many annual leave days do employees receive?"},
    )
    assert response.status_code == 200
    document_ids = [
        item["document_id"] for item in response.json()["sources"]
    ]
    assert "doc-002" in document_ids


def test_cross_tenant_isolation():
    response = client.post(
        "/query",
        headers=HR_HEADERS,
        json={"query": "What are the rules for working remotely?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "org-a"
    assert all(
        item["document_id"] != "doc-005"
        for item in data["sources"]
    )


def test_invalid_top_k_rejected():
    response = client.post(
        "/query",
        headers=ENGINEER_HEADERS,
        json={"query": "deployment", "top_k": 0},
    )
    assert response.status_code == 422


def test_unknown_tenant_is_not_exposed():
    response = client.post(
        "/query",
        headers={"Authorization": "Bearer unknown-tenant-token"},
        json={"query": "deployment"},
    )
    assert response.status_code == 401
