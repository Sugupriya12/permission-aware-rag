import pytest
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
        return {
            "answer": "No authorized documents found.",
            "cited_ids": [],
            "abstained": True,
        }

    doc_id = documents[0]["id"]
    return {
        "answer": f"Test answer [{doc_id}]",
        "cited_ids": [doc_id],
        "abstained": False,
    }


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
def _use_answer(monkeypatch, result):
    """Return a controlled structured answer for one test."""
    monkeypatch.setattr(
        api,
        "generate_answer",
        lambda query, documents: result,
    )


@pytest.mark.parametrize(
    "answer",
    [
        "The available documents do not contain the answer.",
        "I could not verify this information.",
        "There is not enough information to answer.",
        "The documents do not establish this policy.",
    ],
)
def test_abstention_has_no_sources_or_citations(monkeypatch, answer):
    _use_answer(
        monkeypatch,
        {
            "answer": answer,
            "cited_ids": [],
            "abstained": True,
        },
    )

    response = client.post(
        "/query",
        headers=HR_HEADERS,
        json={"query": "How many annual leave days do employees receive?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["sources"] == []
    assert data["result_count"] >= 1


def test_supported_answer_lists_cited_source(monkeypatch):
    _use_answer(
        monkeypatch,
        {
            "answer": "Employees receive 20 days of leave [doc-002].",
            "cited_ids": ["doc-002"],
            "abstained": False,
        },
    )

    response = client.post(
        "/query",
        headers=HR_HEADERS,
        json={"query": "How many annual leave days do employees receive?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert [s["document_id"] for s in data["sources"]] == ["doc-002"]
    assert "[doc-002]" in data["answer"]


def test_only_cited_documents_are_listed(monkeypatch):
    _use_answer(
        monkeypatch,
        {
            "answer": "Employees receive 20 days of leave [doc-002].",
            "cited_ids": ["doc-002"],
            "abstained": False,
        },
    )

    response = client.post(
        "/query",
        headers=HR_HEADERS,
        json={"query": "leave policy", "top_k": 5},
    )

    data = response.json()
    assert len(data["sources"]) == 1
    assert data["sources"][0]["document_id"] == "doc-002"
    assert data["result_count"] >= len(data["sources"])


def test_fabricated_citation_is_rejected(monkeypatch):
    _use_answer(
        monkeypatch,
        {
            "answer": "Some claim [doc-999].",
            "cited_ids": ["doc-999"],
            "abstained": False,
        },
    )

    response = client.post(
        "/query",
        headers=HR_HEADERS,
        json={"query": "How many annual leave days do employees receive?"},
    )

    data = response.json()
    assert data["sources"] == []
    assert data["answer"] == (
        "I could not verify an answer from the "
        "available authorized documents."
    )


def test_model_cannot_leak_unauthorized_document(monkeypatch):
    _use_answer(
        monkeypatch,
        {
            "answer": "Employees receive 20 days of leave [doc-002].",
            "cited_ids": ["doc-002"],
            "abstained": False,
        },
    )

    response = client.post(
        "/query",
        headers=ENGINEER_HEADERS,
        json={"query": "How many annual leave days?"},
    )

    data = response.json()
    assert data["sources"] == []
    assert data["answer"] == (
        "I could not verify an answer from the "
        "available authorized documents."
    )
