
from fastapi.testclient import TestClient
import api

client = TestClient(api.app)

ENGINEER_HEADERS = {
    "Authorization": "Bearer dev-token-engineer"
}

HR_HEADERS = {
    "Authorization": "Bearer dev-token-hr"
}


def test_org_a_engineer_cannot_retrieve_org_b_document():
    response = client.post(
        "/query",
        headers=ENGINEER_HEADERS,
        json={"query": "What are the rules for working remotely?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "org-a"
    assert all(
        source["document_id"] != "doc-005"
        for source in data["sources"]
    )


def test_engineer_cannot_retrieve_hr_only_document():
    response = client.post(
        "/query",
        headers=ENGINEER_HEADERS,
        json={"query": "How many annual leave days do employees receive?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert all(
        source["document_id"] != "doc-002"
        for source in data["sources"]
    )


def test_hr_user_cannot_change_tenant_or_role():
    response = client.post(
        "/query",
        headers=HR_HEADERS,
        json={
            "query": "What are the rules for working remotely?",
            "tenant_id": "org-b",
            "user_role": "admin",
        },
    )

    assert response.status_code == 422


def test_org_b_hr_cannot_access_org_a_hr_document():
    response = client.post(
        "/query",
        headers={
            "Authorization": "Bearer dev-token-org-b-hr"
        },
        json={"query": "How many annual leave days do employees receive?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "org-b"
    assert all(
        source["document_id"] != "doc-002"
        for source in data["sources"]
    )
