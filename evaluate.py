
from app import retrieve


# 25 answerable questions and 5 questions that the documents
# do not contain enough information to answer.
EVALUATION_CASES = [
    # Deployment Procedure: doc-001
    {
        "query": "What is required before production deployment?",
        "tenant_id": "org-a",
        "role": "engineer",
        "expected_docs": ["doc-001"],
    },
    {
        "query": "What approvals are needed to deploy code?",
        "tenant_id": "org-a",
        "role": "engineer",
        "expected_docs": ["doc-001"],
    },
    {
        "query": "Why do we need a rollback plan?",
        "tenant_id": "org-a",
        "role": "engineer",
        "expected_docs": ["doc-001"],
    },
    {
        "query": "Who must approve a production release?",
        "tenant_id": "org-a",
        "role": "engineer",
        "expected_docs": ["doc-001"],
    },
    {
        "query": "What checks must happen before deploying to production?",
        "tenant_id": "org-a",
        "role": "engineer",
        "expected_docs": ["doc-001"],
    },

    # Leave Policy: doc-002
    {
        "query": "How many annual leave days do employees receive?",
        "tenant_id": "org-a",
        "role": "hr",
        "expected_docs": ["doc-002"],
    },
    {
        "query": "How do employees request time off?",
        "tenant_id": "org-a",
        "role": "hr",
        "expected_docs": ["doc-002"],
    },
    {
        "query": "Who approves an employee's leave request?",
        "tenant_id": "org-a",
        "role": "hr",
        "expected_docs": ["doc-002"],
    },
    {
        "query": "Where should staff submit leave requests?",
        "tenant_id": "org-a",
        "role": "hr",
        "expected_docs": ["doc-002"],
    },
    {
        "query": "What is the annual paid leave allowance?",
        "tenant_id": "org-a",
        "role": "hr",
        "expected_docs": ["doc-002"],
    },

    # Expense Reimbursement: doc-004
    {
        "query": "How do employees claim expense reimbursements?",
        "tenant_id": "org-a",
        "role": "finance",
        "expected_docs": ["doc-004"],
    },
    {
        "query": "When must receipts be submitted for expenses?",
        "tenant_id": "org-a",
        "role": "finance",
        "expected_docs": ["doc-004"],
    },
    {
        "query": "Who reviews reimbursement claims?",
        "tenant_id": "org-a",
        "role": "finance",
        "expected_docs": ["doc-004"],
    },
    {
        "query": "How are approved expenses reimbursed?",
        "tenant_id": "org-a",
        "role": "finance",
        "expected_docs": ["doc-004"],
    },
    {
        "query": "What is the deadline for expense receipts?",
        "tenant_id": "org-a",
        "role": "finance",
        "expected_docs": ["doc-004"],
    },

    # Release Procedure: doc-003
    {
        "query": "What is required before releasing a new version?",
        "tenant_id": "org-b",
        "role": "engineer",
        "expected_docs": ["doc-003"],
    },
    {
        "query": "What testing is required before a release?",
        "tenant_id": "org-b",
        "role": "engineer",
        "expected_docs": ["doc-003"],
    },
    {
        "query": "Who owns the software release?",
        "tenant_id": "org-b",
        "role": "engineer",
        "expected_docs": ["doc-003"],
    },
    {
        "query": "What should happen after deployment?",
        "tenant_id": "org-b",
        "role": "engineer",
        "expected_docs": ["doc-003"],
    },
    {
        "query": "What documentation accompanies a release?",
        "tenant_id": "org-b",
        "role": "engineer",
        "expected_docs": ["doc-003"],
    },

    # Remote Work Policy: doc-005
    {
        "query": "What are the rules for working remotely?",
        "tenant_id": "org-b",
        "role": "hr",
        "expected_docs": ["doc-005"],
    },
    {
        "query": "Which devices should remote workers use?",
        "tenant_id": "org-b",
        "role": "hr",
        "expected_docs": ["doc-005"],
    },
    {
        "query": "Who approves working from home?",
        "tenant_id": "org-b",
        "role": "hr",
        "expected_docs": ["doc-005"],
    },
    {
        "query": "What data protection rules apply to remote work?",
        "tenant_id": "org-b",
        "role": "hr",
        "expected_docs": ["doc-005"],
    },
    {
        "query": "What is required to work outside the office?",
        "tenant_id": "org-b",
        "role": "hr",
        "expected_docs": ["doc-005"],
    },

    # Unanswerable from the current five documents
    {
        "query": "What is the company's maternity leave policy?",
        "tenant_id": "org-a",
        "role": "hr",
        "expected_docs": [],
    },
    {
        "query": "What is the salary range for software engineers?",
        "tenant_id": "org-a",
        "role": "hr",
        "expected_docs": [],
    },
    {
        "query": "Which cloud provider hosts our production servers?",
        "tenant_id": "org-a",
        "role": "engineer",
        "expected_docs": [],
    },
    {
        "query": "What is the company's annual revenue?",
        "tenant_id": "org-a",
        "role": "finance",
        "expected_docs": [],
    },
    {
        "query": "How many vacation days can employees carry over?",
        "tenant_id": "org-a",
        "role": "hr",
        "expected_docs": [],
    },
]



def evaluate_retrieval(k_values=(1, 3)):
    answerable_cases = [
        case for case in EVALUATION_CASES
        if case["expected_docs"]
    ]
    unanswerable_cases = [
        case for case in EVALUATION_CASES
        if not case["expected_docs"]
    ]

    hits = {k: 0 for k in k_values}
    total_relevant = sum(
        len(case["expected_docs"]) for case in answerable_cases
    )

    permission_violations = []
    correct_abstentions = 0
    false_acceptances = 0
    false_rejections = 0
    unanswerable_with_candidates = 0

    print("========== ANSWERABLE QUESTIONS ==========")

    for case in answerable_cases:
        expected = set(case["expected_docs"])

        results = retrieve(
            query=case["query"],
            tenant_id=case["tenant_id"],
            user_role=case["role"],
            top_k=max(k_values),
        )

        retrieved_ids = [doc["id"] for doc in results]

        if not results:
            false_rejections += 1

        for doc in results:
            if (
                doc["tenant_id"] != case["tenant_id"]
                or case["role"] not in doc["allowed_roles"]
            ):
                permission_violations.append(
                    (case["query"], doc["id"])
                )

        for k in k_values:
            hits[k] += len(expected & set(retrieved_ids[:k]))

        print(f"\nQuestion: {case['query']}")
        print(f"Expected: {sorted(expected)}")
        print(f"Retrieved: {retrieved_ids}")

    print("\n========== UNANSWERABLE QUESTIONS ==========")

    for case in unanswerable_cases:
        results = retrieve(
            query=case["query"],
            tenant_id=case["tenant_id"],
            user_role=case["role"],
            top_k=max(k_values),
        )

        if results:
            unanswerable_with_candidates += 1
            false_acceptances += 1
        else:
            correct_abstentions += 1

        print(f"\nQuestion: {case['query']}")
        print(f"Retrieved candidates: {[doc['id'] for doc in results]}")

        if results:
            print(f"Top similarity score: {results[0]['score']:.4f}")
        else:
            print("No authorized candidates returned.")

        for doc in results:
            if (
                doc["tenant_id"] != case["tenant_id"]
                or case["role"] not in doc["allowed_roles"]
            ):
                permission_violations.append(
                    (case["query"], doc["id"])
                )

    print("\n========== EVALUATION SUMMARY ==========")

    for k in k_values:
        recall = hits[k] / total_relevant if total_relevant else 0
        print(f"Recall@{k}: {recall:.2%} ({hits[k]}/{total_relevant})")

    print(f"Total questions: {len(EVALUATION_CASES)}")
    print(f"Answerable questions: {len(answerable_cases)}")
    print(f"Unanswerable questions: {len(unanswerable_cases)}")
    print(
        "Unanswerable questions returning candidates: "
        f"{unanswerable_with_candidates}/{len(unanswerable_cases)}"
    )
    print(f"Correct abstentions: {correct_abstentions}")
    print(f"False acceptances: {false_acceptances}")
    print(f"False rejections: {false_rejections}")
    print(f"Permission violations: {len(permission_violations)}")

    if permission_violations:
        print("Violations found:", permission_violations)
    else:
        print("All returned documents passed permission checks.")
if __name__ == "__main__":
    evaluate_retrieval()