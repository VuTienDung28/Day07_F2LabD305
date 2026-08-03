"""Run the reproducible individual evaluation for Lab 7.

The script uses the real multilingual local embedder, evaluates the five
similarity pairs from REPORT_CANHAN.md, and runs the shared five-query
benchmark against all three built-in chunking strategies.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingest import build_knowledge_base  # noqa: E402
from src import (  # noqa: E402
    FixedSizeChunker,
    LocalEmbedder,
    RecursiveChunker,
    SentenceChunker,
    compute_similarity,
)


DATA_DIR = ROOT / "data" / "k3_library"
BENCHMARK_PATH = DATA_DIR / "benchmark.csv"

SIMILARITY_PAIRS = [
    {
        "id": 1,
        "sentence_a": "Sinh viên có thể gia hạn sách trực tuyến.",
        "sentence_b": "Người học được phép kéo dài thời gian mượn tài liệu qua website.",
        "prediction": "Cao",
    },
    {
        "id": 2,
        "sentence_a": "Undergraduate students may borrow three library items.",
        "sentence_b": "The borrowing limit for undergraduate students is three items.",
        "prediction": "Cao",
    },
    {
        "id": 3,
        "sentence_a": "The library explains how to renew a book.",
        "sentence_b": "Renewable energy reduces fossil-fuel consumption.",
        "prediction": "Thấp",
    },
    {
        "id": 4,
        "sentence_a": "Sinh viên đại học được mượn sách trong hai tuần.",
        "sentence_b": "Undergraduate students may borrow books for two weeks.",
        "prediction": "Cao",
    },
    {
        "id": 5,
        "sentence_a": "Course Reserve materials may be used for two hours.",
        "sentence_b": "The weather forecast predicts heavy rain tomorrow.",
        "prediction": "Thấp",
    },
]


def parse_filter(raw_filter: str) -> dict[str, str] | None:
    raw_filter = raw_filter.strip()
    if not raw_filter:
        return None
    result: dict[str, str] = {}
    for condition in raw_filter.split(";"):
        key, separator, value = condition.partition("=")
        if not separator:
            raise ValueError(f"Invalid metadata filter: {raw_filter!r}")
        result[key.strip()] = value.strip()
    return result


def load_benchmark() -> list[dict[str, str]]:
    with BENCHMARK_PATH.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def compact(text: str, limit: int = 220) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else normalized[: limit - 3] + "..."


def run_similarity(embedder: LocalEmbedder) -> list[dict]:
    results: list[dict] = []
    for pair in SIMILARITY_PAIRS:
        vector_a = embedder(pair["sentence_a"])
        vector_b = embedder(pair["sentence_b"])
        score = compute_similarity(vector_a, vector_b)
        results.append({**pair, "score": round(score, 6)})
    return results


def run_retrieval(embedder: LocalEmbedder, benchmark: list[dict[str, str]]) -> dict:
    strategies = {
        "fixed_size_500_overlap_50": FixedSizeChunker(chunk_size=500, overlap=50),
        "sentence_3": SentenceChunker(max_sentences_per_chunk=3),
        "recursive_500": RecursiveChunker(chunk_size=500),
    }

    evaluation: dict[str, dict] = {}
    for strategy_name, chunker in strategies.items():
        store = build_knowledge_base(
            DATA_DIR,
            embedding_fn=embedder,
            chunker=chunker,
            collection_name=f"personal_{strategy_name}",
        )

        query_results: list[dict] = []
        hit_count = 0
        reciprocal_rank_total = 0.0
        for item in benchmark:
            metadata_filter = parse_filter(item.get("metadata_filter", ""))
            if metadata_filter:
                results = store.search_with_filter(
                    item["query"],
                    top_k=3,
                    metadata_filter=metadata_filter,
                )
            else:
                results = store.search(item["query"], top_k=3)

            expected_doc_id = Path(item["evidence_file"]).stem
            evidence_rank = next(
                (
                    rank
                    for rank, result in enumerate(results, start=1)
                    if result["metadata"].get("doc_id") == expected_doc_id
                ),
                None,
            )
            if evidence_rank is not None:
                hit_count += 1
                reciprocal_rank_total += 1.0 / evidence_rank

            query_results.append(
                {
                    "id": int(item["id"]),
                    "query": item["query"],
                    "gold_answer": item["gold_answer"],
                    "expected_doc_id": expected_doc_id,
                    "metadata_filter": metadata_filter,
                    "evidence_rank": evidence_rank,
                    "relevant_in_top3": evidence_rank is not None,
                    "results": [
                        {
                            "rank": rank,
                            "doc_id": result["metadata"].get("doc_id"),
                            "score": round(result["score"], 6),
                            "content": compact(result["content"]),
                        }
                        for rank, result in enumerate(results, start=1)
                    ],
                }
            )

        evaluation[strategy_name] = {
            "chunk_count": store.get_collection_size(),
            "top3_evidence_hits": hit_count,
            "mean_reciprocal_rank": round(reciprocal_rank_total / len(benchmark), 6),
            "queries": query_results,
        }
    return evaluation


def main() -> None:
    embedder = LocalEmbedder()
    benchmark = load_benchmark()
    report = {
        "embedding_backend": embedder._backend_name,
        "embedding_dimension": len(embedder("embedding dimension check")),
        "similarity": run_similarity(embedder),
        "retrieval": run_retrieval(embedder, benchmark),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
