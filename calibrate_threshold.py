
from app import retrieve
from evaluate import EVALUATION_CASES


thresholds = [0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55]

samples = []

for case in EVALUATION_CASES:
    results = retrieve(
        query=case["query"],
        tenant_id=case["tenant_id"],
        user_role=case["role"],
        top_k=1,
        min_score=0.0,
    )

    top_doc = results[0] if results else None

    samples.append({
        "query": case["query"],
        "tenant_id": case["tenant_id"],
        "role": case["role"],
        "answerable": bool(case["expected_docs"]),
        "score": top_doc["score"] if top_doc else None,
        "doc_id": top_doc["id"] if top_doc else None,
        "doc_title": top_doc["title"] if top_doc else None,
    })


print("\nRETRIEVAL DIAGNOSTICS")
print("-" * 90)

for sample in samples:
    if not sample["answerable"]:
        print(f"\nQuestion: {sample['query']}")
        print(f"Tenant / role: {sample['tenant_id']} / {sample['role']}")

        if sample["score"] is None:
            print("Top candidate: None")
        else:
            print(
                f"Top candidate: {sample['doc_id']} - "
                f"{sample['doc_title']}"
            )
            print(f"Similarity score: {sample['score']:.4f}")


print("\nTHRESHOLD COMPARISON")
print("-" * 85)
print(
    f"{'Threshold':>10} | {'Answerable accepted':>20} | "
    f"{'Unanswerable rejected':>22} | {'False rejections':>16}"
)

for threshold in thresholds:
    answerable = [s for s in samples if s["answerable"]]
    unanswerable = [s for s in samples if not s["answerable"]]

    accepted_answerable = sum(
        s["score"] is not None and s["score"] >= threshold
        for s in answerable
    )

    rejected_unanswerable = sum(
        s["score"] is None or s["score"] < threshold
        for s in unanswerable
    )

    false_rejections = len(answerable) - accepted_answerable

    print(
        f"{threshold:10.2f} | "
        f"{accepted_answerable:>5}/{len(answerable):<14} | "
        f"{rejected_unanswerable:>5}/{len(unanswerable):<16} | "
        f"{false_rejections:>16}"
    )

print("\nNote: Results apply only to this small evaluation dataset.")
