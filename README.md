# Permission-Aware Multi-Tenant RAG

A retrieval-augmented generation (RAG) system for internal company documents, designed with tenant isolation, role-based access control, grounded answers, and citation validation.

## Overview

Traditional RAG systems retrieve documents based primarily on semantic similarity. In a multi-tenant environment, this can expose information to users who should not have access to it.

This project enforces document permissions **before retrieval and ranking**, then uses an LLM to generate answers grounded in authorized documents. If the available evidence does not support an answer, the system abstains instead of inventing information.

## Key Features

- **Multi-tenant isolation:** Documents are filtered by tenant before semantic retrieval.
- **Role-based access control:** Users can retrieve only documents permitted for their roles.
- **Semantic search:** Sentence embeddings and cosine similarity rank relevant documents.
- **Grounded answers:** Gemini generates answers from supplied document context.
- **Citation validation:** Responses are checked for valid and consistent document citations.
- **Safe abstention:** Unsupported questions and invalid model responses produce safe fallback responses.
- **Authenticated API:** FastAPI endpoints use bearer-token authentication.
- **Document ingestion:** Supports PDF, TXT, MD, and Markdown files, with upload validation and document metadata.
- **Evaluation suite:** Measures retrieval quality, answer correctness, abstention, citation validity, and access-control behavior.
- **Prompt-injection testing:** Includes automated tests and an opt-in live Gemini test.

## Architecture

1. A user submits a question with an authenticated request.
2. The system identifies the user's tenant and role from the authentication token.
3. Unauthorized documents are excluded before semantic ranking.
4. The remaining documents are ranked by similarity and filtered by a relevance threshold.
5. Gemini generates a structured answer using the retrieved context.
6. Citation and response validation checks are applied before the API returns the result.
7. If the evidence is insufficient or validation fails, the system abstains.

## Tech Stack

- Python
- FastAPI
- Sentence Transformers (`all-MiniLM-L6-v2`)
- scikit-learn cosine similarity
- Google Gemini API
- Pytest
- PyPDF
- Portalocker

## Project Structure

```text
permission-aware-rag/
├── api.py
├── app.py
├── llm.py
├── ingest.py
├── documents.json
├── evaluate.py
├── evaluate_answers.py
├── calibrate_threshold.py
├── test_api.py
├── test_llm.py
├── test_rag.py
├── test_security.py
├── test_prompt_injection.py
├── test_prompt_injection_live.py
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd permission-aware-rag
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure the API key

Create a `.env` file in the project root:

```text
GEMINI_API_KEY=your_api_key_here
```

Obtain your own API key through Google AI Studio. Never commit your actual `.env` file or expose your API key.

### 5. Start the API

```powershell
uvicorn api:app --reload
```

Open the interactive API documentation at:

`http://127.0.0.1:8000/docs`

## API Usage

### Query documents

Send a POST request to `/query` with a bearer token and a JSON body containing the question and optional `top_k` value.

Example request body:

```json
{
  "query": "How many annual leave days do employees receive?",
  "top_k": 3
}
```

Use the development tokens configured in `api.py` when running the local demonstration. These tokens are for development only and must not be used as production authentication credentials.

### Upload documents

Use the document upload endpoint exposed by the FastAPI application. Uploads are authenticated and subject to role restrictions, file-type validation, and a file-size limit.

Document tenant ownership is derived from the authenticated user rather than accepted from an untrusted upload request.

## Evaluation

Latest recorded local evaluation results:

| Metric | Result |
|---|---:|
| Retrieval Recall@1 | 96% (24/25) |
| Retrieval Recall@3 | 100% (25/25) |
| Permission violations | 0 observed |
| False rejections | 0 observed |
| Unanswerable retrieval rate | 40% (2/5) |
| Answer-quality diagnostic | 11/11 passed |

The answer-quality diagnostic recorded five supported answers and six correct abstentions, with valid citations in all 11 cases.

These results come from a small local benchmark and should not be interpreted as proof of production-level security or general performance. The unanswerable retrieval rate indicates that related documents can still be retrieved for questions they do not answer.

### Run automated tests

```powershell
pytest -q
```

### Run retrieval evaluation

```powershell
python evaluate.py
```

### Run answer-quality evaluation

```powershell
python evaluate_answers.py
```

### Run the live prompt-injection test

This test makes a real Gemini API request and may incur API usage.

```powershell
$env:RUN_LIVE_LLM_TESTS="1"
pytest -q -s test_prompt_injection_live.py
```

The live test is opt-in and is skipped during the normal test run unless explicitly enabled.

## Security Considerations

- Enforce tenant and role authorization before document retrieval.
- Validate citations against the documents supplied to the model.
- Treat retrieved document contents as untrusted data, not instructions.
- Fail safely when model responses are malformed or unsupported.
- Keep API keys out of source control.
- Use proper identity management, token expiry, secret management, persistent storage, and production-grade authorization before deployment.

The local development tokens are not a substitute for a production identity provider. Prompt-injection tests provide useful evidence but do not guarantee complete resistance to prompt injection.

## Current Limitations

- The evaluation datasets are small and may not represent real-world traffic.
- Semantic retrieval can return related but insufficient evidence.
- Answer correctness checks do not constitute comprehensive factual verification.
- Development authentication and local JSON storage require hardening before production use.
- Deployment and production monitoring are not covered by the current local evaluation.

## Future Improvements

- Improve retrieval precision and evaluate alternative retrieval strategies.
- Expand adversarial, authorization, and answer-grounding benchmarks.
- Add production-grade authentication and persistent storage.
- Introduce monitoring, structured logging, and deployment automation.
- Evaluate performance on larger and more diverse document collections.

## Author

Developed as an AI engineering portfolio project exploring secure RAG systems, access-controlled retrieval, LLM grounding, and evaluation.
