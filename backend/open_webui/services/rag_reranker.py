"""
RAG transparency and reranking

Provides:
- Lexical reranking (BM25-style) for retrieved chunks
- Transparent logging of retrieval and reranking
- Sources panel data for UI
"""

import math
import re
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RAGChunk(BaseModel):
    """RAG chunk with metadata"""
    doc_id: str
    doc_title: Optional[str] = None
    doc_path: Optional[str] = None
    chunk_id: str
    content: str
    vector_score: float
    metadata: Optional[Dict[str, Any]] = None


class RankedChunk(BaseModel):
    """Chunk with reranking score"""
    chunk: RAGChunk
    vector_score: float
    rerank_score: float
    final_score: float
    preview: str  # First 200-500 chars


class RerankerResult(BaseModel):
    """Reranker output"""
    ranked_chunks: List[RankedChunk]
    reranker_type: str
    rerank_latency_ms: float


class LexicalReranker:
    """
    Lexical reranker using BM25-inspired scoring.

    Combines vector retrieval scores with lexical overlap to improve relevance.
    """

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        vector_weight: float = 0.3,
        lexical_weight: float = 0.7
    ):
        """
        Args:
            k1: Term frequency saturation parameter
            b: Length normalization parameter
            vector_weight: Weight for vector score (0-1)
            lexical_weight: Weight for lexical score (0-1)
        """
        self.k1 = k1
        self.b = b
        self.vector_weight = vector_weight
        self.lexical_weight = lexical_weight

    def rerank(
        self,
        query: str,
        chunks: List[RAGChunk],
        top_k: Optional[int] = None
    ) -> RerankerResult:
        """
        Rerank chunks based on lexical overlap with query.

        Args:
            query: User query
            chunks: Retrieved chunks
            top_k: Number of top chunks to return (None = all)

        Returns:
            RerankerResult with ranked chunks
        """
        start_time = time.time()

        if not chunks:
            return RerankerResult(
                ranked_chunks=[],
                reranker_type="lexical_bm25",
                rerank_latency_ms=0
            )

        # Tokenize query
        query_tokens = self._tokenize(query)
        query_term_freq = Counter(query_tokens)

        # Calculate average document length
        doc_lengths = [len(self._tokenize(chunk.content)) for chunk in chunks]
        avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0

        # Calculate IDF for query terms
        idf_scores = self._calculate_idf(query_term_freq.keys(), chunks)

        # Score each chunk
        ranked = []
        for chunk, doc_length in zip(chunks, doc_lengths):
            lexical_score = self._bm25_score(
                query_term_freq,
                chunk.content,
                doc_length,
                avg_doc_length,
                idf_scores
            )

            # Normalize vector score to 0-1 range
            normalized_vector = chunk.vector_score

            # Combine scores
            final_score = (
                self.vector_weight * normalized_vector +
                self.lexical_weight * lexical_score
            )

            # Generate preview (first 400 chars)
            preview = chunk.content[:400]
            if len(chunk.content) > 400:
                preview += "..."

            ranked.append(RankedChunk(
                chunk=chunk,
                vector_score=chunk.vector_score,
                rerank_score=lexical_score,
                final_score=final_score,
                preview=preview
            ))

        # Sort by final score
        ranked.sort(key=lambda x: x.final_score, reverse=True)

        # Take top K
        if top_k:
            ranked = ranked[:top_k]

        latency_ms = (time.time() - start_time) * 1000

        return RerankerResult(
            ranked_chunks=ranked,
            reranker_type="lexical_bm25",
            rerank_latency_ms=latency_ms
        )

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Convert to lowercase and split on non-alphanumeric
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens

    def _calculate_idf(self, query_terms: List[str], chunks: List[RAGChunk]) -> Dict[str, float]:
        """Calculate IDF (Inverse Document Frequency) for query terms"""
        N = len(chunks)
        idf_scores = {}

        for term in query_terms:
            # Count documents containing term
            doc_count = sum(
                1 for chunk in chunks
                if term in self._tokenize(chunk.content)
            )

            # IDF formula: log((N - df + 0.5) / (df + 0.5))
            if doc_count > 0:
                idf_scores[term] = math.log((N - doc_count + 0.5) / (doc_count + 0.5))
            else:
                idf_scores[term] = 0

        return idf_scores

    def _bm25_score(
        self,
        query_term_freq: Counter,
        document: str,
        doc_length: int,
        avg_doc_length: float,
        idf_scores: Dict[str, float]
    ) -> float:
        """Calculate BM25 score for document"""
        doc_tokens = self._tokenize(document)
        doc_term_freq = Counter(doc_tokens)

        score = 0.0

        for term, query_freq in query_term_freq.items():
            if term not in doc_term_freq:
                continue

            # Term frequency in document
            tf = doc_term_freq[term]

            # Length normalization
            norm = 1 - self.b + self.b * (doc_length / avg_doc_length) if avg_doc_length > 0 else 1

            # BM25 formula
            term_score = (
                idf_scores.get(term, 0) *
                (tf * (self.k1 + 1)) /
                (tf + self.k1 * norm)
            )

            score += term_score

        # Normalize to 0-1 range (approximate)
        # Max possible score is roughly sum(idf) * (k1 + 1)
        max_score = sum(idf_scores.values()) * (self.k1 + 1)
        if max_score > 0:
            score = min(score / max_score, 1.0)

        return score


class RAGTransparency:
    """
    RAG transparency wrapper that logs retrieval and reranking
    for observability.
    """

    def __init__(self, reranker: Optional[LexicalReranker] = None):
        self.reranker = reranker or LexicalReranker()

    def retrieve_and_rerank(
        self,
        query: str,
        retrieved_chunks: List[RAGChunk],
        top_k: int = 5,
        knowledge_base_id: Optional[str] = None
    ) -> Tuple[List[RankedChunk], RerankerResult]:
        """
        Retrieve, rerank, and prepare transparency data.

        Args:
            query: User query
            retrieved_chunks: Chunks from vector retrieval
            top_k: Number of chunks to select for prompt
            knowledge_base_id: Optional KB identifier

        Returns:
            Tuple of (selected_chunks, reranker_result)
        """
        if not retrieved_chunks:
            logger.info("No chunks retrieved for RAG")
            return [], RerankerResult(
                ranked_chunks=[],
                reranker_type="none",
                rerank_latency_ms=0
            )

        # Rerank
        rerank_result = self.reranker.rerank(query, retrieved_chunks, top_k=top_k)

        logger.info(
            f"RAG: Retrieved {len(retrieved_chunks)} chunks, "
            f"reranked and selected top {len(rerank_result.ranked_chunks)} "
            f"(rerank latency: {rerank_result.rerank_latency_ms:.1f}ms)"
        )

        return rerank_result.ranked_chunks, rerank_result

    def format_sources_for_ui(self, ranked_chunks: List[RankedChunk]) -> List[Dict[str, Any]]:
        """
        Format ranked chunks for UI sources panel.

        Returns:
            List of source dictionaries for frontend
        """
        sources = []
        for i, ranked_chunk in enumerate(ranked_chunks, start=1):
            chunk = ranked_chunk.chunk
            sources.append({
                "rank": i,
                "doc_id": chunk.doc_id,
                "doc_title": chunk.doc_title or "Unknown",
                "doc_path": chunk.doc_path,
                "chunk_id": chunk.chunk_id,
                "preview": ranked_chunk.preview,
                "vector_score": round(ranked_chunk.vector_score, 3),
                "rerank_score": round(ranked_chunk.rerank_score, 3),
                "final_score": round(ranked_chunk.final_score, 3),
                "metadata": chunk.metadata
            })
        return sources

    def inject_chunks_into_prompt(
        self,
        messages: List[Dict[str, Any]],
        ranked_chunks: List[RankedChunk],
        injection_strategy: str = "system"
    ) -> List[Dict[str, Any]]:
        """
        Inject RAG chunks into prompt messages.

        Args:
            messages: Original messages
            ranked_chunks: Reranked chunks to inject
            injection_strategy: "system" or "user" (where to inject)

        Returns:
            Modified messages with injected context
        """
        if not ranked_chunks:
            return messages

        # Build context from chunks
        context_parts = []
        for i, ranked_chunk in enumerate(ranked_chunks, start=1):
            chunk = ranked_chunk.chunk
            doc_title = chunk.doc_title or chunk.doc_id
            context_parts.append(
                f"[Source {i}: {doc_title}]\n{chunk.content}\n"
            )

        context = "\n".join(context_parts)

        # Create injection message
        injection_content = (
            f"You have access to the following relevant information from the knowledge base. "
            f"Use this context to provide accurate and grounded responses:\n\n{context}"
        )

        # Inject based on strategy
        modified_messages = messages.copy()

        if injection_strategy == "system":
            # Add as system message at start
            modified_messages.insert(0, {
                "role": "system",
                "content": injection_content
            })
        elif injection_strategy == "user":
            # Add to first user message
            for msg in modified_messages:
                if msg.get("role") == "user":
                    original_content = msg.get("content", "")
                    msg["content"] = f"{injection_content}\n\n---\n\nUser question: {original_content}"
                    break

        return modified_messages


# Global reranker instance
_rag_transparency: Optional[RAGTransparency] = None


def get_rag_transparency() -> RAGTransparency:
    """Get or create global RAG transparency instance"""
    global _rag_transparency
    if _rag_transparency is None:
        _rag_transparency = RAGTransparency()
    return _rag_transparency
