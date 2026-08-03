from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)

        context_sections: list[str] = []
        for index, result in enumerate(results, start=1):
            metadata = result.get("metadata", {})
            source = metadata.get("source_url") or metadata.get("source") or "unknown"
            doc_id = metadata.get("doc_id") or result.get("id", "unknown")
            context_sections.append(
                f"[{index}] doc_id={doc_id}; source={source}\n{result['content']}"
            )

        context = "\n\n".join(context_sections)
        if not context:
            context = "No relevant context was retrieved from the knowledge base."

        prompt = (
            "You are a knowledge-base assistant. Answer the question using only "
            "the retrieved context below. If the context is insufficient, say "
            "that the knowledge base does not contain enough information. Do not "
            "invent facts.\n\n"
            f"RETRIEVED CONTEXT:\n{context}\n\n"
            f"QUESTION:\n{question}\n\n"
            "ANSWER:"
        )
        return self.llm_fn(prompt)
