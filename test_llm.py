
from llm import generate_answer

sample_documents = [
    {
        "id": "doc-001",
        "title": "Deployment Procedure",
        "content": (
            "Production deployments require code review, "
            "automated tests, engineering lead approval, "
            "and a rollback plan."
        ),
    }
]

answer = generate_answer(
    "What is required before production deployment?",
    sample_documents,
)

print("\nGenerated answer:\n")
print(answer)

assert "doc-001" in answer
