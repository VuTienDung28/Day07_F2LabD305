"""Run the locked K3 library benchmark with one personal chunking strategy.

The shared corpus, benchmark queries, embedder and evaluation flow stay fixed.
For a fair comparison, team members should change only the marked ``chunker``
assignment in ``main``.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from ingest import build_knowledge_base
from src import KnowledgeBaseAgent, LocalEmbedder, RecursiveChunker


DEFAULT_DATA_DIR = Path("data/k3_library")
DEFAULT_BENCHMARK = DEFAULT_DATA_DIR / "benchmark.csv"
DEFAULT_OUTPUT = Path("results/vu_tien_dung_recursive.json")


def _parse_metadata_filter(raw_filter: str) -> dict[str, str] | None:
    """Parse the benchmark CSV's ``key=value`` metadata filter."""
    raw_filter = raw_filter.strip()
    if not raw_filter:
        return None
    key, separator, value = raw_filter.partition("=")
    if not separator or not key.strip() or not value.strip():
        raise ValueError(f"Invalid metadata filter: {raw_filter!r}")
    return {key.strip(): value.strip()}


def _preview(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else f"{compact[: limit - 3]}..."


def _extractive_llm(prompt: str) -> str:
    """Return grounded context lines without calling an external chat service."""
    question = prompt.split("Question:", 1)[1].split("Answer:", 1)[0].strip()
    context = prompt.split("Context:", 1)[1].split("Question:", 1)[0]
    stop_words = {
        "what", "how", "many", "may", "an", "a", "the", "is", "are",
        "for", "and", "after", "it", "one", "at", "to", "do", "does",
        "when", "should", "user", "item", "items", "library",
    }
    query_terms = {
        word
        for word in re.findall(r"[a-z0-9]+", question.lower())
        if len(word) > 2 and word not in stop_words
    }

    candidates: list[tuple[int, int, str]] = []
    for position, raw_line in enumerate(context.splitlines()):
        line = raw_line.strip().strip("-").strip()
        if not line or line.startswith("[Context") or line.startswith("#"):
            continue
        line_terms = set(re.findall(r"[a-z0-9]+", line.lower()))
        overlap = len(query_terms & line_terms)
        if overlap:
            candidates.append((overlap, -position, line))

    candidates.sort(reverse=True)
    selected = [line for _, _, line in candidates[:3]]
    if not selected:
        return "The retrieved context does not contain enough information."
    return " ".join(selected)


class _RetrievedContextStore:
    """Expose one pre-filtered result set through the Agent's search contract."""

    def __init__(self, results: list[dict[str, Any]]) -> None:
        self._results = results

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        del query
        return self._results[:top_k]


def _serialize_result(result: dict[str, Any]) -> dict[str, Any]:
    metadata = result["metadata"]
    return {
        "score": round(float(result["score"]), 6),
        "doc_id": metadata.get("doc_id"),
        "chunk_index": metadata.get("chunk_index"),
        "source": metadata.get("source"),
        "preview": _preview(result["content"]),
        "content": result["content"],
    }


def run_benchmark(
    data_dir: Path,
    benchmark_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    embedder = LocalEmbedder()

    # PERSONAL STRATEGY: this is the only assignment team members should change.
    chunker = RecursiveChunker(separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""], chunk_size=500)

    store = build_knowledge_base(
        data_dir,
        embedding_fn=embedder,
        chunker=chunker,
        collection_name="vu-tien-dung-k3-library",
    )

    with benchmark_path.open(encoding="utf-8", newline="") as handle:
        benchmark_rows = list(csv.DictReader(handle))
    if len(benchmark_rows) != 5:
        raise ValueError(f"Expected exactly 5 benchmark queries, got {len(benchmark_rows)}")

    payload: dict[str, Any] = {
        "owner": "Vũ Tiến Dũng",
        "corpus": str(data_dir).replace("\\", "/"),
        "benchmark": str(benchmark_path).replace("\\", "/"),
        "embedding_backend": embedder._backend_name,
        "strategy": {
            "chunker": "RecursiveChunker",
            "chunk_size": chunker.chunk_size,
            "separators": chunker.separators,
        },
        "collection_size": store.get_collection_size(),
        "queries": [],
    }

    print(f"Owner: {payload['owner']}")
    print(f"Embedding backend: {payload['embedding_backend']}")
    print(f"Strategy: {payload['strategy']}")
    print(f"Chunks loaded: {payload['collection_size']}")

    for row in benchmark_rows:
        query = row["query"]
        metadata_filter = _parse_metadata_filter(row["metadata_filter"])
        unfiltered = store.search(query, top_k=3)
        if metadata_filter:
            top_three = store.search_with_filter(
                query,
                top_k=3,
                metadata_filter=metadata_filter,
            )
        else:
            top_three = unfiltered

        evidence_doc_id = Path(row["evidence_file"]).stem
        evidence_sections = [
            section.strip()
            for section in row["evidence_section"].split(";")
            if section.strip()
        ]
        matched_sections = [
            section
            for section in evidence_sections
            if any(section in result["content"] for result in top_three)
        ]
        agent = KnowledgeBaseAgent(
            store=_RetrievedContextStore(top_three),  # type: ignore[arg-type]
            llm_fn=_extractive_llm,
        )
        agent_answer = agent.answer(query, top_k=3)

        query_result = {
            "id": int(row["id"]),
            "query": query,
            "gold_answer": row["gold_answer"],
            "evidence_file": row["evidence_file"],
            "evidence_section": row["evidence_section"],
            "metadata_filter": metadata_filter,
            "evidence_doc_in_top3": any(
                result["metadata"].get("doc_id") == evidence_doc_id
                for result in top_three
            ),
            "matched_evidence_sections": matched_sections,
            "unfiltered_top3": [_serialize_result(result) for result in unfiltered],
            "top3": [_serialize_result(result) for result in top_three],
            "agent_answer": agent_answer,
        }
        payload["queries"].append(query_result)

        print(f"\nQ{row['id']}: {query}")
        print(f"Filter: {metadata_filter}")
        for rank, result in enumerate(query_result["top3"], start=1):
            print(
                f"  {rank}. score={result['score']:.6f} "
                f"doc_id={result['doc_id']} chunk_index={result['chunk_index']}"
            )
            print(f"     {result['preview']}")
        print(f"Evidence document in top-3: {query_result['evidence_doc_in_top3']}")
        print(f"Matched evidence headings: {matched_sections}")
        print(f"Agent answer: {agent_answer}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nRaw benchmark result written to: {output_path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    run_benchmark(args.data_dir, args.benchmark, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
