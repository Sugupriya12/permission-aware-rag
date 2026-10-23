
import json
from pathlib import Path

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

DATA_PATH = Path(__file__).with_name("documents.json")

with DATA_PATH.open(encoding="utf-8") as f:
    DOCUMENTS = json.load(f)

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

document_embeddings = model.encode(
    [doc["content"] for doc in DOCUMENTS],
    normalize_embeddings=True,
)



def retrieve(
    query: str,
    tenant_id: str,
    user_role: str,
    top_k: int = 3,
    min_score: float = 0.30,
) -> list[dict]:
    # 1. Enforce access control before semantic ranking.
    authorized_indices = [
        i
        for i, doc in enumerate(DOCUMENTS)
        if doc["tenant_id"] == tenant_id
        and user_role in doc["allowed_roles"]
    ]

    if not authorized_indices:
        return []

    # 2. Embed the query.
    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
    )

    # 3. Rank only documents the user is allowed to access.
    authorized_embeddings = document_embeddings[authorized_indices]

    scores = cosine_similarity(
        query_embedding,
        authorized_embeddings,
    )[0]

    ranked_positions = scores.argsort()[::-1]

    # 4. Keep only sufficiently relevant authorized documents.
    results = []

    for position in ranked_positions:
        score = float(scores[position])

        if score < min_score:
            continue

        results.append({
            **DOCUMENTS[authorized_indices[position]],
            "score": score,
        })

        if len(results) >= top_k:
            break

    return results



if __name__ == "__main__":
    while True:
        query = input("\nQuestion (or 'exit'): ").strip()

        if query.lower() == "exit":
            break

        tenant_id = input("Tenant ID (org-a / org-b): ").strip()
        user_role = input("Role (engineer / hr / finance / admin): ").strip()

        results = retrieve(query, tenant_id, user_role)

        if not results:
            print("No authorized documents found.")
            continue

        for doc in results:
            print(
                f"\n[{doc['score']:.3f}] {doc['title']}"
                f"\n{doc['content']}"
            )
