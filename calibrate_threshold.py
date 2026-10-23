
from app import retrieve
from evaluate import EVALUATION_CASES


thresholds = [0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55]

# Collect the highest-ranked document's score for each question.
samples = []

for case in EVALUATION_CASES:
    results = retrieve(
        query=case["query"],
        tenant_id=case["tenant_id"],
        user_role=case["role"],
        top_k=1,
    )

    score = results[0]["score"] if results else None
    answerable = bool(case["expected_docs"])

    samples.append({
        "query": case["query"],
        "answerable": answerable,
        "score": score,
    })


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

print("\nInterpretation:")
print("- Accepted answerable = questions whose top score passes the threshold.")
print("- Rejected unanswerable = questions whose top score falls below it.")
print("- False rejections = answerable questions incorrectly filtered out.")
print("These results apply only to this small evaluation dataset.")
