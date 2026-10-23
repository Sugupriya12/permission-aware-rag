
import json
import re
from pathlib import Path

import portalocker
from pypdf import PdfReader

DATA_FILE = Path(__file__).resolve().parent / "documents.json"
LOCK_FILE = DATA_FILE.with_suffix(".json.lock")

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}


def read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(
            page.extract_text() or "" for page in reader.pages
        ).strip()

    return path.read_text(encoding="utf-8").strip()


def ingest_file(
    file_path: str,
    tenant_id: str,
    department: str,
    allowed_roles: list[str],
) -> dict:
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Supported formats: PDF, TXT, MD, Markdown")

    tenant_id = tenant_id.strip()
    department = department.strip()

    if not tenant_id or not department:
        raise ValueError("tenant_id and department are required")

    roles = {
        role.strip()
        for role in allowed_roles
        if role.strip()
    }

    if not roles:
        raise ValueError("Provide at least one non-empty allowed role")

    content = read_file(path)

    if not content:
        raise ValueError("The file contains no extractable text")

    # Lock document ID generation and saving together.
    with portalocker.Lock(str(LOCK_FILE), mode="a", timeout=10):
        if DATA_FILE.exists():
            documents = json.loads(
                DATA_FILE.read_text(encoding="utf-8")
            )
        else:
            documents = []

        if not isinstance(documents, list):
            raise ValueError("documents.json must contain a JSON list")

        existing_ids = {doc["id"] for doc in documents}

        numbers = [
            int(match.group(1))
            for doc_id in existing_ids
            if isinstance(doc_id, str)
            and (match := re.fullmatch(r"doc-(\d+)", doc_id))
        ]

        next_number = max(numbers, default=0) + 1

        while f"doc-{next_number:03d}" in existing_ids:
            next_number += 1

        document = {
            "id": f"doc-{next_number:03d}",
            "tenant_id": tenant_id,
            "department": department,
            "allowed_roles": sorted(roles),
            "title": path.stem,
            "content": content,
        }

        documents.append(document)

        DATA_FILE.write_text(
            json.dumps(documents, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return {
        "id": document["id"],
        "title": document["title"],
        "tenant_id": document["tenant_id"],
        "department": document["department"],
        "allowed_roles": document["allowed_roles"],
    }


if __name__ == "__main__":
    print("Import this module and call ingest_file() from your application.")
