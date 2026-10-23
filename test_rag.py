
from app import retrieve


def test_tenant_isolation():
    results = retrieve(
        "How do I deploy code to production?",
        tenant_id="org-a",
        user_role="engineer",
    )

    assert results
    assert all(doc["tenant_id"] == "org-a" for doc in results)


def test_role_restriction():
    results = retrieve(
        "How many annual leave days do employees receive?",
        tenant_id="org-a",
        user_role="engineer",
    )

    assert all(doc["id"] != "doc-002" for doc in results)


def test_authorized_hr_access():
    results = retrieve(
        "How many annual leave days do employees receive?",
        tenant_id="org-a",
        user_role="hr",
    )

    assert any(doc["id"] == "doc-002" for doc in results)


def test_cross_tenant_document_denied():
    results = retrieve(
        "What are the rules for working remotely?",
        tenant_id="org-a",
        user_role="hr",
    )

    assert all(doc["tenant_id"] == "org-a" for doc in results)
    assert all(doc["id"] != "doc-005" for doc in results)


def test_unknown_tenant_returns_no_documents():
    results = retrieve(
        "deployment procedure",
        tenant_id="unknown-org",
        user_role="engineer",
    )

    assert results == []
