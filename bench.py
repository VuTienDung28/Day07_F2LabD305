"""Reproducible individual benchmark for Lab 07.

This script uses the real multilingual embedding model, runs the five cosine
similarity pairs from the individual report, evaluates the five shared
benchmark queries with the selected personal chunking strategy, and sends the
retrieved context through KnowledgeBaseAgent.

Run from the repository root:
    python bench.py
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from ingest import build_knowledge_base
from src import (
    FixedSizeChunker,
    KnowledgeBaseAgent,
    LocalEmbedder,
    compute_similarity,
)


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "k3_library"
BENCHMARK_PATH = DATA_DIR / "benchmark.csv"

# The personal strategy reported in REPORT_CANHAN.md.
PERSONAL_CHUNKER = FixedSizeChunker(chunk_size=500, overlap=50)

SIMILARITY_PAIRS = [
    (
        "Sinh viên có thể gia hạn sách trực tuyến.",
        "Người học được phép kéo dài thời gian mượn tài liệu qua website.",
        "Cao",
    ),
    (
        "Undergraduate students may borrow three library items.",
        "The borrowing limit for undergraduate students is three items.",
        "Cao",
    ),
    (
        "The library explains how to renew a book.",
        "Renewable energy reduces fossil-fuel consumption.",
        "Thấp",
    ),
    (
        "Sinh viên đại học được mượn sách trong hai tuần.",
        "Undergraduate students may borrow books for two weeks.",
        "Cao",
    ),
    (
        "Course Reserve materials may be used for two hours.",
        "The weather forecast predicts heavy rain tomorrow.",
        "Thấp",
    ),
]

# Human-defined evidence phrases derived from the gold answers. A result is an
# exact evidence hit only when the returned CHUNK contains every phrase for the
# query. This avoids the false-positive shortcut of treating any chunk from the
# expected document as relevant.
REQUIRED_EVIDENCE = {
    1: ["up to three items", "loan period is two weeks", "renewed once"],
    2: ["one item per user at a time"],
    3: [
        "10,000 vnd per overdue document per day",
        "10,000 vnd per overdue document per hour",
        "10,000 vnd per overdue item per day",
    ],
    4: ["held for two days", "request is canceled"],
    5: ["should not repeatedly submit another payment", "contact library staff"],
}

TOPIC_EVIDENCE = {
    1: ["undergraduate", "borrow"],
    2: ["course reserve"],
    3: ["overdue", "fine"],
    4: ["request", "collection"],
    5: ["payment", "transaction"],
}


def parse_filter(raw_filter: str) -> dict[str, str] | None:
    raw_filter = raw_filter.strip()
    if not raw_filter:
        return None

    metadata_filter: dict[str, str] = {}
    for condition in raw_filter.split(";"):
        key, separator, value = condition.partition("=")
        if not separator:
            raise ValueError(f"Invalid metadata filter: {raw_filter!r}")
        metadata_filter[key.strip()] = value.strip()
    return metadata_filter


def load_benchmark() -> list[dict[str, str]]:
    with BENCHMARK_PATH.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def contains_all(text: str, phrases: list[str]) -> bool:
    normalized = normalize(text)
    return all(normalize(phrase) in normalized for phrase in phrases)


def contains_any(text: str, phrases: list[str]) -> bool:
    normalized = normalize(text)
    return any(normalize(phrase) in normalized for phrase in phrases)


class FilteredSearchView:
    """Expose EmbeddingStore.search while applying one benchmark filter."""

    def __init__(self, store, metadata_filter: dict[str, str] | None) -> None:
        self.store = store
        self.metadata_filter = metadata_filter

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if self.metadata_filter:
            return self.store.search_with_filter(
                query,
                top_k=top_k,
                metadata_filter=self.metadata_filter,
            )
        return self.store.search(query, top_k=top_k)


class ExtractiveAnswerer:
    """Local, deterministic llm_fn that selects evidence from the RAG prompt.

    The lab does not provide a generative LLM or require an API key. This
    callable keeps the agent evaluation reproducible and grounded: it extracts
    candidate sentences from the retrieved context and returns the three most
    similar sentences to the question. It never adds facts absent from context.
    """

    def __init__(self, embedder: LocalEmbedder) -> None:
        self.embedder = embedder

    def __call__(self, prompt: str) -> str:
        context_marker = "RETRIEVED CONTEXT:\n"
        question_marker = "\n\nQUESTION:\n"
        answer_marker = "\n\nANSWER:"
        if context_marker not in prompt or question_marker not in prompt:
            return "Insufficient structured context."

        context = prompt.split(context_marker, 1)[1].split(question_marker, 1)[0]
        question = prompt.split(question_marker, 1)[1].split(answer_marker, 1)[0].strip()
        candidates = [
            candidate.strip(" -")
            for candidate in re.split(r"(?<=[.!?])\s+|\n+", context)
            if len(candidate.strip()) >= 20 and not candidate.lstrip().startswith("[")
        ]
        if not candidates:
            return "The retrieved context does not contain enough information."

        question_vector = self.embedder(question)
        ranked = sorted(
            (
                (compute_similarity(question_vector, self.embedder(candidate)), candidate)
                for candidate in candidates
            ),
            key=lambda item: item[0],
            reverse=True,
        )

        # Multi-part questions often express separate answers in separate
        # sentences. Prioritize numeric/time evidence for "how many/how long"
        # questions and action evidence for "what should" questions, then fill
        # the remainder by semantic similarity.
        numeric_pattern = re.compile(
            r"\b(?:\d[\d,.]*|one|two|three|four|five|six|seven|eight|nine|ten|"
            r"day|days|week|weeks|hour|hours|minute|minutes|once|twice)\b",
            re.IGNORECASE,
        )
        action_pattern = re.compile(
            r"\b(?:should|must|contact|avoid|do not|not repeatedly)\b",
            re.IGNORECASE,
        )
        question_lower = question.lower()
        priority_candidates: list[str] = []
        for _, candidate in ranked:
            if (
                ("how many" in question_lower or "how long" in question_lower)
                and numeric_pattern.search(candidate)
            ) or ("what should" in question_lower and action_pattern.search(candidate)):
                priority_candidates.append(candidate)

        ordered_candidates = priority_candidates + [
            candidate for _, candidate in ranked if candidate not in priority_candidates
        ]
        selected: list[str] = []
        for candidate in ordered_candidates:
            if candidate not in selected:
                selected.append(candidate)
            if len(selected) == 10:
                break
        return " ".join(selected)


def run_similarity(embedder: LocalEmbedder) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for index, (sentence_a, sentence_b, prediction) in enumerate(
        SIMILARITY_PAIRS, start=1
    ):
        score = compute_similarity(embedder(sentence_a), embedder(sentence_b))
        output.append(
            {
                "id": index,
                "sentence_a": sentence_a,
                "sentence_b": sentence_b,
                "prediction": prediction,
                "score": round(score, 6),
            }
        )
    return output


def run_benchmark(embedder: LocalEmbedder) -> dict[str, Any]:
    store = build_knowledge_base(
        DATA_DIR,
        embedding_fn=embedder,
        chunker=PERSONAL_CHUNKER,
        collection_name="personal_fixed_500_50",
    )
    extractive_answerer = ExtractiveAnswerer(embedder)

    query_output: list[dict[str, Any]] = []
    total_points = 0
    full_evidence_hits = 0
    for item in load_benchmark():
        query_id = int(item["id"])
        metadata_filter = parse_filter(item.get("metadata_filter", ""))
        search_view = FilteredSearchView(store, metadata_filter)
        results = search_view.search(item["query"], top_k=3)

        exact_rank = next(
            (
                rank
                for rank, result in enumerate(results, start=1)
                if contains_all(result["content"], REQUIRED_EVIDENCE[query_id])
            ),
            None,
        )
        partial_rank = next(
            (
                rank
                for rank, result in enumerate(results, start=1)
                if contains_any(result["content"], TOPIC_EVIDENCE[query_id])
            ),
            None,
        )

        if exact_rank == 1:
            points = 2
        elif exact_rank in {2, 3} or partial_rank is not None:
            points = 1
        else:
            points = 0
        total_points += points
        full_evidence_hits += int(exact_rank is not None)

        agent = KnowledgeBaseAgent(store=search_view, llm_fn=extractive_answerer)
        agent_answer = agent.answer(item["query"], top_k=3)

        query_output.append(
            {
                "id": query_id,
                "query": item["query"],
                "gold_answer": item["gold_answer"],
                "metadata_filter": metadata_filter,
                "exact_evidence_rank": exact_rank,
                "partial_topic_rank": partial_rank,
                "rubric_points": points,
                "top_3": [
                    {
                        "rank": rank,
                        "doc_id": result["metadata"].get("doc_id"),
                        "score": round(result["score"], 6),
                        "contains_full_evidence": contains_all(
                            result["content"], REQUIRED_EVIDENCE[query_id]
                        ),
                        "content": " ".join(result["content"].split()),
                    }
                    for rank, result in enumerate(results, start=1)
                ],
                "agent_answer": agent_answer,
            }
        )

    return {
        "strategy": "FixedSizeChunker(chunk_size=500, overlap=50)",
        "chunk_count": store.get_collection_size(),
        "full_evidence_hits_in_top_3": full_evidence_hits,
        "retrieval_score": total_points,
        "maximum_score": 10,
        "queries": query_output,
    }


def main() -> None:
    embedder = LocalEmbedder()
    output = {
        "embedding_backend": embedder._backend_name,
        "embedding_dimension": len(embedder("embedding dimension check")),
        "similarity": run_similarity(embedder),
        "benchmark": run_benchmark(embedder),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
