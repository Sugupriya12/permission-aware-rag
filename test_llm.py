import json

import llm


def test_generate_answer_validates_structured_response(monkeypatch):
    sample_documents = [
        {
            "id": "doc-001",
            "title": "Deployment Procedure",
            "content": "Production deployments require code review.",
        }
    ]

    fake_response = type(
        "FakeResponse",
        (),
        {
            "text": json.dumps({
                "answer": "Production deployments require code review [doc-001].",
                "cited_ids": ["doc-001"],
                "abstained": False,
            })
        },
    )()

    monkeypatch.setattr(
        llm.client.models,
        "generate_content",
        lambda **kwargs: fake_response,
    )

    result = llm.generate_answer(
        "What is required before deployment?",
        sample_documents,
    )

    assert result["abstained"] is False
    assert result["cited_ids"] == ["doc-001"]
    assert "[doc-001]" in result["answer"]


def test_generate_answer_fails_safe_on_malformed_json(monkeypatch):
    fake_response = type(
        "FakeResponse",
        (),
        {"text": "This is not JSON"},
    )()

    monkeypatch.setattr(
        llm.client.models,
        "generate_content",
        lambda **kwargs: fake_response,
    )

    result = llm.generate_answer(
        "What is required before deployment?",
        [
            {
                "id": "doc-001",
                "title": "Deployment Procedure",
                "content": "Production deployments require code review.",
            }
        ],
    )

    assert result["abstained"] is True
    assert result["cited_ids"] == []
    assert "[doc-" not in result["answer"]


def test_generate_answer_abstains_without_documents():
    result = llm.generate_answer("Unknown question", [])

    assert result["abstained"] is True
    assert result["cited_ids"] == []

def test_generate_answer_rejects_unauthorized_citation(monkeypatch):
    import json
    import llm

    class FakeResponse:
        text = json.dumps({
            "answer": "Employees receive 20 days of annual leave [doc-999].",
            "cited_ids": ["doc-999"],
            "abstained": False,
        })

    class FakeModels:
        def generate_content(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(llm, "client", FakeClient())

    documents = [{
        "id": "doc-002",
        "title": "Leave Policy",
        "content": "Employees receive 20 days of annual leave.",
    }]

    result = llm.generate_answer(
        "How many annual leave days do employees receive?",
        documents,
    )

    assert result["abstained"] is True
    assert result["cited_ids"] == []


def test_generate_answer_rejects_inconsistent_citations(monkeypatch):
    import json
    import llm

    class FakeResponse:
        text = json.dumps({
            "answer": "Employees receive 20 days of annual leave.",
            "cited_ids": ["doc-002"],
            "abstained": False,
        })

    class FakeModels:
        def generate_content(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(llm, "client", FakeClient())

    documents = [{
        "id": "doc-002",
        "title": "Leave Policy",
        "content": "Employees receive 20 days of annual leave.",
    }]

    result = llm.generate_answer(
        "How many annual leave days do employees receive?",
        documents,
    )

    assert result["abstained"] is True
    assert result["cited_ids"] == []
