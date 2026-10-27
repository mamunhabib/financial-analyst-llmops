"""
=============================================================================
FILE ROLE & CALL CHAIN CONTEXT:
- Role: Upstash Vector Index Client for Financial SEC 10-K RAG
- Where this file is used / Who calls it:
    1. Called by: src/rag/ingest.py
       (Upserts 384-dimensional dense vectors and metadata chunks during 10-K ingestion)
    2. Called by: src/tools/rag_tool.py
       (The ReAct Agent tool invokes client.query() to retrieve financial disclosures)
    3. Used in Agent Reasoning: src/handlers/react_core.py
       (When user queries require Apple, Microsoft, or Nvidia SEC 10-K filings)
=============================================================================
"""

from typing import Any, Dict, List, Optional, Union
import logging
from upstash_vector import Index, Vector

from config.settings import settings

logger = logging.getLogger(__name__)


class UpstashVectorClient:
    """
    Client for Upstash Vector database.
    Manages vector upsertion, similarity queries with metadata filters, and index stats.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        top_k: int = None,
    ):
        self.url = url or settings.UPSTASH_VECTOR_REST_URL
        self.token = token or settings.UPSTASH_VECTOR_REST_TOKEN
        self.top_k = top_k or settings.VECTOR_TOP_K

        if not self.url or not self.token:
            logger.warning("Upstash Vector credentials not fully configured in settings.")

        self._index: Optional[Index] = None

    @property
    def index(self) -> Index:
        """Lazy-loaded Upstash Index instance."""
        if self._index is None:
            if not self.url or not self.token:
                raise ValueError("UPSTASH_VECTOR_REST_URL and UPSTASH_VECTOR_REST_TOKEN must be set.")
            self._index = Index(url=self.url, token=self.token)
        return self._index

    def upsert_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 100) -> int:
        """
        Upsert a batch of document chunks into Upstash Vector.
        Each chunk dict must contain:
          - 'id': str
          - 'vector': List[float] (384-dimensional)
          - 'metadata': Dict[str, Any] (must include 'text', 'ticker', 'year', 'section')
        """
        if not chunks:
            return 0

        total_upserted = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            vector_tuples = []
            for item in batch:
                vector_tuples.append(
                    Vector(
                        id=str(item["id"]),
                        vector=item["vector"],
                        metadata=item.get("metadata", {}),
                    )
                )

            self.index.upsert(vectors=vector_tuples)
            total_upserted += len(batch)
            logger.info(f"Upserted batch of {len(batch)} vectors to Upstash (total: {total_upserted})")

        return total_upserted

    def query(
        self,
        vector: Union[List[float], str],
        top_k: Optional[int] = None,
        filter_expr: Optional[str] = None,
        include_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Query Upstash Vector for the nearest neighbors.

        Args:
            vector: Either a raw query string (e.g. "What are Apple's supply chain risks?")
                    OR a 384-dimensional dense float vector. If a string is provided,
                    it is automatically converted to embeddings via EmbeddingEngine.
            top_k: Number of nearest matches to retrieve (defaults to settings.VECTOR_TOP_K).
            filter_expr: SQL-like metadata filter string (e.g. "ticker = 'AAPL'").
            include_metadata: Whether to return chunk text and metadata.

        Returns:
            List of dicts: [{'id': str, 'score': float, 'metadata': dict, 'text': str}]
        """
        # If caller passed raw text string instead of float list, auto-embed it
        if isinstance(vector, str):
            from src.rag.embeddings import EmbeddingClient
            embedder = EmbeddingClient()
            vector = embedder.embed_query(vector)

        k = top_k or self.top_k

        try:
            query_kwargs = {
                "vector": vector,
                "top_k": k,
                "include_metadata": include_metadata,
            }
            if filter_expr:
                query_kwargs["filter"] = filter_expr

            results = self.index.query(**query_kwargs)

            formatted_results = []
            for res in results:
                metadata = getattr(res, "metadata", {}) or {}
                formatted_results.append({
                    "id": getattr(res, "id", ""),
                    "score": getattr(res, "score", 0.0),
                    "metadata": metadata,
                    "text": metadata.get("text", ""),
                    "ticker": metadata.get("ticker", ""),
                    "year": metadata.get("year", ""),
                    "section": metadata.get("section", ""),
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Error querying Upstash Vector: {e}")
            raise

    def get_info(self) -> Dict[str, Any]:
        """Retrieve vector index metadata and current vector count."""
        try:
            info = self.index.info()
            return {
                "vector_count": getattr(info, "vector_count", 0),
                "dimension": getattr(info, "dimension", 0),
                "similarity_function": getattr(info, "similarity_function", ""),
            }
        except Exception as e:
            logger.error(f"Failed to fetch Upstash Vector info: {e}")
            return {"error": str(e)}

    def reset(self) -> None:
        """Reset / delete all vectors in the index (useful for fresh ingestion)."""
        logger.warning("Resetting Upstash Vector index...")
        self.index.reset()


# Global singleton instance
vector_client = UpstashVectorClient()
