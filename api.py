import shutil
import tempfile
from pathlib import Path

from fastapi import File, Form, UploadFile
from llm import generate_answer
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from app import retrieve
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
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

    result = generate_answer(query, results)

    # Validate the structured result before returning anything.
    if (
        not isinstance(result, dict)
        or not isinstance(result.get("answer"), str)
        or not result["answer"].strip()
        or not isinstance(result.get("cited_ids"), list)
        or not all(
            isinstance(doc_id, str)
            for doc_id in result["cited_ids"]
        )
        or not isinstance(result.get("abstained"), bool)
    ):
        result = {
            "answer": (
                "I could not verify an answer from the "
                "available authorized documents."
            ),
            "cited_ids": [],
            "abstained": True,
        }

    answer = result["answer"]
    cited_ids = set(result["cited_ids"])
    abstained = result["abstained"]

    # Defense in depth: cited documents must be among the
    # documents authorized and retrieved for this user.
    retrieved_ids = {doc["id"] for doc in results}

    if abstained or not cited_ids or not cited_ids.issubset(retrieved_ids):
        answer = (
            "I could not verify an answer from the "
            "available authorized documents."
        )
        cited_ids = set()
        abstained = True

    sources = [
        {
            "document_id": doc["id"],
            "title": doc["title"],
            "score": round(doc["score"], 4),
        }
        for doc in results
        if not abstained and doc["id"] in cited_ids
    ]

    return {
        "query": query,
        "user_id": user["user_id"],
        "tenant_id": user["tenant_id"],
        "answer": answer,
        "sources": sources,
        "result_count": len(results),
    }

@app.post("/documents/upload")
def upload_document(
    file: UploadFile = File(...),
    department: str = Form(...),
    allowed_roles: str = Form(...),
    user: dict = Depends(get_current_user),
):
    if user["role"] not in {"hr", "admin"}:
        raise HTTPException(
            status_code=403,
            detail="Only HR/admin users can upload documents",
        )

    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()

    if suffix not in {".pdf", ".txt", ".md", ".markdown"}:
        raise HTTPException(
            status_code=400,
            detail="Supported formats: PDF, TXT, Markdown",
        )

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / f"upload{suffix}"
            file.file.seek(0)
            size = 0
            with temp_path.open("wb") as output:
                while chunk := file.file.read(64 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_SIZE:
                        raise HTTPException(
                            status_code=413,
                            detail="File too large. Maximum upload size is 5 MB.",
                              )
                    output.write(chunk)


            from ingest import ingest_file

            valid_roles = {"hr", "engineer", "finance"}
            if user["role"] == "admin":
                valid_roles.add("admin")
            roles = {
                role.strip().lower()
                for role in allowed_roles.split(",")
                if role.strip()
            }

            if not roles:
                raise HTTPException(
                    status_code=400,
                    detail="At least one allowed role is required",
                )

            invalid_roles = roles - valid_roles
            if invalid_roles:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid roles: {', '.join(sorted(invalid_roles))}",
                )

            result = ingest_file(
                file_path=str(temp_path),
                tenant_id=user["tenant_id"],
                department=department,
                allowed_roles=sorted(roles),
            )

            return {
                "message": "Document uploaded successfully",
                "document": result,
            }

    except (ValueError, OSError) as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc
    finally:
        file.file.close()
