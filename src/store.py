from __future__ import annotations

import importlib
from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

        try:
            chromadb = importlib.import_module("chromadb")

            client = chromadb.EphemeralClient()
            self._collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._use_chroma = True
        except Exception:
            self._use_chroma = False
            self._collection = None

    def _make_record(self, doc: Document) -> dict[str, Any]:
        record_id = f"{doc.id}:{self._next_index}"
        self._next_index += 1
        return {
            "id": record_id,
            "content": doc.content,
            "metadata": {**doc.metadata, "doc_id": doc.id},
            "embedding": self._embedding_fn(doc.content),
        }

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        query_embedding = self._embedding_fn(query)
        results = [
            {
                "id": record["id"],
                "content": record["content"],
                "metadata": record["metadata"].copy(),
                "score": _dot(query_embedding, record["embedding"]),
            }
            for record in records
        ]
        return sorted(results, key=lambda result: result["score"], reverse=True)[:top_k]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        records = [self._make_record(doc) for doc in docs]
        if not records:
            return
        if self._use_chroma:
            collection = self._collection
            assert collection is not None
            collection.add(
                ids=[record["id"] for record in records],
                documents=[record["content"] for record in records],
                metadatas=[record["metadata"] for record in records],
                embeddings=[record["embedding"] for record in records],
            )
        else:
            self._store.extend(records)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        if top_k <= 0:
            return []
        if not self._use_chroma:
            return self._search_records(query, self._store, top_k)

        size = self.get_collection_size()
        if size == 0:
            return []
        collection = self._collection
        assert collection is not None
        result = collection.query(
            query_embeddings=[self._embedding_fn(query)],
            n_results=min(top_k, size),
            include=["documents", "metadatas", "distances"],
        )
        if not result["ids"]:
            return []
        return [
            {
                "id": record_id,
                "content": content,
                "metadata": metadata,
                "score": 1.0 - distance,
            }
            for record_id, content, metadata, distance in zip(
                result["ids"][0],
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
            )
        ]

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        if self._use_chroma:
            collection = self._collection
            assert collection is not None
            return collection.count()
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict | None = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if not metadata_filter:
            return self.search(query, top_k)
        if top_k <= 0:
            return []
        if not self._use_chroma:
            records = [
                record
                for record in self._store
                if all(record["metadata"].get(key) == value for key, value in metadata_filter.items())
            ]
            return self._search_records(query, records, top_k)

        size = self.get_collection_size()
        if size == 0:
            return []
        collection = self._collection
        assert collection is not None
        result = collection.query(
            query_embeddings=[self._embedding_fn(query)],
            n_results=min(top_k, size),
            where=metadata_filter,
            include=["documents", "metadatas", "distances"],
        )
        if not result["ids"]:
            return []
        return [
            {
                "id": record_id,
                "content": content,
                "metadata": metadata,
                "score": 1.0 - distance,
            }
            for record_id, content, metadata, distance in zip(
                result["ids"][0],
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
            )
        ]

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        if self._use_chroma:
            collection = self._collection
            assert collection is not None
            matches = collection.get(where={"doc_id": doc_id}, include=[])
            if not matches["ids"]:
                return False
            collection.delete(ids=matches["ids"])
            return True

        original_size = len(self._store)
        self._store = [record for record in self._store if record["metadata"].get("doc_id") != doc_id]
        return len(self._store) < original_size
