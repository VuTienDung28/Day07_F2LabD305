"""Compare individual chunking strategies on the K3 library benchmark.

The experiment uses one shared, L2-normalized TF-IDF vector space as an
offline lexical embedding baseline.  Replace ``make_embedding_fn`` with a
LocalEmbedder when the multilingual model is available; the chunking and
evaluation code can stay unchanged.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingest import chunk_document, load_documents  # noqa: E402
from src import (  # noqa: E402
    Document,
    EmbeddingStore,
    FixedSizeChunker,
    LocalEmbedder,
    RecursiveChunker,
)


DATA_DIR = ROOT / "data" / "k3_library"
BENCHMARK_PATH = DATA_DIR / "benchmark.csv"

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "be",
    "been",
    "being",
    "for",
    "from",
    "in",
    "is",
    "it",
    "its",
    "may",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "when",
}
NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
}
ANSWER_TOKEN_COVERAGE = 0.65


class SentenceOverlapChunker:
    """Group complete sentences and repeat a configurable number at boundaries."""

    def __init__(self, sentences_per_chunk: int = 4, overlap_sentences: int = 1) -> None:
        if sentences_per_chunk <= 0:
            raise ValueError("sentences_per_chunk must be greater than 0")
        if not 0 <= overlap_sentences < sentences_per_chunk:
            raise ValueError("overlap_sentences must be in [0, sentences_per_chunk)")
        self.sentences_per_chunk = sentences_per_chunk
        self.overlap_sentences = overlap_sentences

    def chunk(self, text: str) -> list[str]:
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])(?:[ \t]+|\n+)", text.strip())
            if sentence.strip()
        ]
        if not sentences:
            return []

        step = self.sentences_per_chunk - self.overlap_sentences
        chunks: list[str] = []
        for start in range(0, len(sentences), step):
            piece = " ".join(sentences[start : start + self.sentences_per_chunk])
            if piece:
                chunks.append(piece)
            if start + self.sentences_per_chunk >= len(sentences):
                break
        return chunks


class HeadingAwareChunker:
    """Keep each Markdown heading with chunks created from its section body."""

    HEADING_PATTERN = re.compile(r"(?m)^#{1,6}\s+.+$")

    def __init__(self, chunk_size: int = 500) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []

        matches = list(self.HEADING_PATTERN.finditer(text))
        if not matches:
            return RecursiveChunker(chunk_size=self.chunk_size).chunk(text)

        chunks: list[str] = []
        preamble = text[: matches[0].start()].strip()
        if preamble:
            chunks.extend(RecursiveChunker(chunk_size=self.chunk_size).chunk(preamble))

        for index, match in enumerate(matches):
            heading = match.group(0).strip()
            section_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[match.end() : section_end].strip()
            if not body:
                chunks.append(heading)
                continue

            body_budget = max(1, self.chunk_size - len(heading) - 1)
            for body_chunk in RecursiveChunker(chunk_size=body_budget).chunk(body):
                chunks.append(f"{heading}\n{body_chunk}")
        return chunks


@dataclass
class StrategyResult:
    name: str
    chunk_count: int
    average_length: float
    extra_characters_percent: float
    ranks: list[int | None]
    top_results: list[dict]

    def hits_at(self, k: int) -> int:
        return sum(rank is not None and rank <= k for rank in self.ranks)

    @property
    def mrr_at_5(self) -> float:
        return sum(1 / rank for rank in self.ranks if rank is not None and rank <= 5) / len(
            self.ranks
        )


def load_benchmark() -> list[dict[str, str]]:
    with BENCHMARK_PATH.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_metadata_filter(raw_filter: str) -> dict[str, str] | None:
    if not raw_filter.strip():
        return None
    key, separator, value = raw_filter.partition("=")
    if not separator:
        raise ValueError(f"Invalid metadata filter: {raw_filter}")
    return {key.strip(): value.strip()}


def answer_tokens(text: str) -> set[str]:
    """Return normalized content tokens used by the answer-coverage metric."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {
        NUMBER_WORDS.get(token, token)
        for token in tokens
        if token not in STOP_WORDS
    }


def make_embedding_fn(
    texts: list[str], provider: str
) -> tuple[Callable[[str], list[float]], str]:
    if provider == "local":
        embedder = LocalEmbedder()
        return embedder, f"{embedder._backend_name} (normalized multilingual embeddings)"

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        norm="l2",
        strip_accents="unicode",
        sublinear_tf=True,
    )
    vectorizer.fit(texts)

    def embed(text: str) -> list[float]:
        return vectorizer.transform([text]).toarray()[0].tolist()

    return embed, f"L2-normalized TF-IDF (1-2 grams), vocabulary={len(vectorizer.vocabulary_)}"


def build_chunk_sets(
    documents: list[Document], strategies: dict[str, object]
) -> dict[str, list[Document]]:
    return {
        strategy_name: [
            chunk
            for document in documents
            for chunk in chunk_document(document, chunker)
        ]
        for strategy_name, chunker in strategies.items()
    }


def evaluate_strategy(
    name: str,
    chunk_docs: list[Document],
    benchmark: list[dict[str, str]],
    embedding_fn: Callable[[str], list[float]],
    source_character_count: int,
) -> StrategyResult:
    store = EmbeddingStore(collection_name=f"experiment_{name}", embedding_fn=embedding_fn)
    store.add_documents(chunk_docs)
    ranks: list[int | None] = []
    top_results: list[dict] = []

    for item in benchmark:
        metadata_filter = parse_metadata_filter(item["metadata_filter"])
        if metadata_filter:
            results = store.search_with_filter(
                item["query"], top_k=5, metadata_filter=metadata_filter
            )
        else:
            results = store.search(item["query"], top_k=5)

        top_result = results[0]
        top_results.append(
            {
                "query_id": item["id"],
                "doc_id": top_result["metadata"].get("doc_id"),
                "score": top_result["score"],
                "preview": " ".join(top_result["content"].split())[:120],
            }
        )

        expected_doc_id = Path(item["evidence_file"]).stem
        expected_tokens = answer_tokens(item["gold_answer"])
        rank = None
        for top_k in range(1, 6):
            evidence_text = " ".join(
                result["content"]
                for result in results[:top_k]
                if result["metadata"].get("doc_id") == expected_doc_id
            )
            retrieved_tokens = answer_tokens(evidence_text)
            coverage = len(expected_tokens & retrieved_tokens) / len(expected_tokens)
            if coverage >= ANSWER_TOKEN_COVERAGE:
                rank = top_k
                break
        ranks.append(rank)

    total_chunk_characters = sum(len(document.content) for document in chunk_docs)
    return StrategyResult(
        name=name,
        chunk_count=len(chunk_docs),
        average_length=total_chunk_characters / len(chunk_docs),
        extra_characters_percent=(total_chunk_characters / source_character_count - 1) * 100,
        ranks=ranks,
        top_results=top_results,
    )


def print_results(results: list[StrategyResult], embedding_label: str) -> None:
    print(f"Embedding: {embedding_label}")
    print(f"AnswerHit threshold: {ANSWER_TOKEN_COVERAGE:.0%} normalized gold-token coverage")
    print()
    print("| Strategy | Chunks | Avg chars | Extra chars | Hit@1 | Hit@3 | Hit@5 | MRR@5 |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for result in results:
        print(
            f"| {result.name} | {result.chunk_count} | {result.average_length:.1f} | "
            f"{result.extra_characters_percent:+.1f}% | {result.hits_at(1)}/5 | "
            f"{result.hits_at(3)}/5 | {result.hits_at(5)}/5 | {result.mrr_at_5:.3f} |"
        )

    selected = max(
        results,
        key=lambda result: (
            result.hits_at(3),
            result.hits_at(1),
            result.mrr_at_5,
            -result.chunk_count,
        ),
    )
    print()
    print(f"Selected strategy: {selected.name}")
    print()
    print("| top_k | Relevant queries covered | Additional chunks sent per query |")
    print("|---:|---:|---:|")
    for top_k in (1, 2, 3, 5):
        print(f"| {top_k} | {selected.hits_at(top_k)}/5 | {top_k} |")
    print()
    print("Selected-strategy evidence ranks:", selected.ranks)
    print()
    print("| Query | Top-1 doc_id | Score | Chunk preview |")
    print("|---:|---|---:|---|")
    for detail in selected.top_results:
        print(
            f"| {detail['query_id']} | {detail['doc_id']} | {detail['score']:.3f} | "
            f"{detail['preview'].replace('|', '/')} |"
        )
    print()
    for result in results:
        print(f"{result.name} answer-evidence ranks: {result.ranks}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--embedding",
        choices=("tfidf", "local"),
        default="tfidf",
        help="Embedding backend used for every strategy in this run.",
    )
    args = parser.parse_args()

    documents = load_documents(DATA_DIR)
    benchmark = load_benchmark()
    strategies = {
        "fixed_500_o0": FixedSizeChunker(chunk_size=500, overlap=0),
        "fixed_500_o100": FixedSizeChunker(chunk_size=500, overlap=100),
        "sentence_4_o0": SentenceOverlapChunker(4, 0),
        "sentence_4_o1": SentenceOverlapChunker(4, 1),
        "recursive_500": RecursiveChunker(chunk_size=500),
        "heading_recursive_500": HeadingAwareChunker(chunk_size=500),
    }
    chunk_sets = build_chunk_sets(documents, strategies)
    embedding_texts = [
        document.content for chunk_docs in chunk_sets.values() for document in chunk_docs
    ] + [item["query"] for item in benchmark]
    embedding_fn, embedding_label = make_embedding_fn(embedding_texts, args.embedding)
    source_character_count = sum(len(document.content) for document in documents)

    results = [
        evaluate_strategy(
            name,
            chunk_sets[name],
            benchmark,
            embedding_fn,
            source_character_count,
        )
        for name in strategies
    ]
    print_results(results, embedding_label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
