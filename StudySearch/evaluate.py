"""python evaluate.py：固定问题、页级标注、相同分词下比较两种排序。"""
import csv
import json
import platform
import statistics
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from app import SearchIndex, extract_pdf, tokenize

ROOT = Path(__file__).resolve().parent

def run():
    pdf = ROOT / "samples/study_notes.pdf"
    chunks, warnings = extract_pdf(pdf.name, pdf.read_bytes())
    index = SearchIndex(chunks)
    questions = list(csv.DictReader((ROOT / "evaluation/questions.csv").open(encoding="utf-8")))
    rows, summary = [], {}
    for method in ["keyword", "tfidf"]:
        index.search("预热查询", method)
        records = []
        for q in questions:
            gold = {int(p) for p in q["relevant_pages"].split(";") if p}
            timings = []
            for _ in range(20):
                start = time.perf_counter()
                results = index.search(q["query"], method, 5)
                timings.append((time.perf_counter() - start) * 1000)
            pages = [r["page"] for r in results]
            rank = next((i for i, p in enumerate(pages, 1) if p in gold), None)
            row = {**q, "method": method, "returned_pages": ";".join(map(str, pages)),
                   "hit_at_1": int(bool(pages) and pages[0] in gold) if gold else "",
                   "hit_at_5": int(rank is not None) if gold else "",
                   "reciprocal_rank_at_5": 1 / rank if rank else 0 if gold else "",
                   "returned_any": int(bool(results)), "median_ms": statistics.median(timings)}
            records.append(row)
            rows.append(row)
        answerable = [r for r in records if r["category"] != "unanswerable"]
        unknown = [r for r in records if r["category"] == "unanswerable"]
        summary[method] = {
            "hit_at_1": statistics.mean(r["hit_at_1"] for r in answerable),
            "hit_at_5": statistics.mean(r["hit_at_5"] for r in answerable),
            "mrr_at_5": statistics.mean(r["reciprocal_rank_at_5"] for r in answerable),
            "median_query_ms": statistics.median(r["median_ms"] for r in records),
            "unanswerable_return_rate": statistics.mean(r["returned_any"] for r in unknown),
            "by_category": {cat: statistics.mean(r["hit_at_5"] for r in answerable if r["category"] == cat)
                            for cat in ["direct", "paraphrase"]}}
    with (ROOT / "evaluation/results.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "environment": {"python": platform.python_version(), "platform": platform.platform(),
                              "packages": {p: version(p) for p in ["PyMuPDF", "jieba", "scikit-learn", "streamlit"]}},
              "documents": 1, "chunks": len(chunks), "answerable_questions": 20,
              "unanswerable_questions": 4, "repetitions_per_query": 20, "metrics": summary,
              "limitations": "自编小样本，页级人工预设标注，非独立真实课程评测；耗时不含索引、UI和PDF解析。"}
    (ROOT / "evaluation/summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    run()
