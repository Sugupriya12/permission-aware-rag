from llm import generate_answer
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from app import retrieve

app = FastAPI(
    title="Permission-Aware Multi-Tenant RAG",
    description="Authenticated document retrieval with tenant and role-based access control.",
    version="0.2.0",
)

security = HTTPBearer()

# Development-only token registry.
# In production, use a proper identity provider and securely managed credentials.
USERS = {
    "dev-token-engineer": {
        "user_id": "user-001",
        "tenant_id": "org-a",
        "role": "engineer",
    },
    "dev-token-hr": {
        "user_id": "user-002",
        "tenant_id": "org-a",
        "role": "hr",
    },
    "dev-token-org-b-hr": {
        "user_id": "user-003",
        "tenant_id": "org-b",
        "role": "hr",
    },
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    user = USERS.get(credentials.credentials)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=10)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query")
def query_documents(
    request: QueryRequest,
    user: dict = Depends(get_current_user),
):
    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=422,
            detail="Query must not be blank.",
        )

    results = retrieve(
        query=query,
        tenant_id=user["tenant_id"],
        user_role=user["role"],
        top_k=request.top_k,
    )
    answer = generate_answer(query, results)

    return {
        "query": query,
        "user_id": user["user_id"],
        "tenant_id": user["tenant_id"],
        "answer": answer,
        "sources": [
            {
                "document_id": doc["id"],
                "title": doc["title"],
                "score": round(doc["score"], 4),
            }
            for doc in results
        ],
        "result_count": len(results),
    }