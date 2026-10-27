"""
Embeddings Client Module for Financial & Market Analyst Agent.
Provides 384-dimensional dense vectors for Upstash Vector RAG indexing and search.
Uses fastembed (BAAI/bge-small-en-v1.5 ONNX) with automatic Hugging Face fallback.
"""

from typing import List, Union
import logging
import time
import httpx
import numpy as np

from config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """
    High-Performance Embedding Client.
    Produces 384-dimensional normalized dense vectors matching Upstash Vector index.
    Defaults to local FastEmbed ONNX runtime (0 latency, 0 cost, 0 API limits).
    """

    def __init__(
        self,
        token: str = None,
        model_name: str = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.token = token or settings.HF_TOKEN
        self.model_name = model_name or settings.HF_EMBEDDING_MODEL
        self.timeout = timeout
        self.max_retries = max_retries
        self.expected_dim = 384

        self._fastembed_model = None
        self._init_fastembed()

    def _init_fastembed(self):
        """Initialize local fastembed ONNX runtime if available."""
        try:
            from fastembed import TextEmbedding
            # BAAI/bge-small-en-v1.5 produces exactly 384 dimensions
            self._fastembed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            logger.info("FastEmbed BAAI/bge-small-en-v1.5 initialized successfully.")
        except Exception as e:
            logger.warning(f"FastEmbed initialization skipped: {e}. Falling back to HTTP API.")
            self._fastembed_model = None

    def _normalize_vector(self, vec: Union[List[float], np.ndarray]) -> List[float]:
        """Ensures embedding is a 1D list of 384 floats, L2 normalized."""
        arr = np.array(vec, dtype=np.float32)

        if arr.ndim == 2:
            arr = np.mean(arr, axis=0)
        elif arr.ndim > 2:
            arr = arr.reshape(-1, self.expected_dim).mean(axis=0)

        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm

        vector_list = arr.tolist()

        if len(vector_list) != self.expected_dim:
            raise ValueError(
                f"Dimension mismatch: expected {self.expected_dim}, got {len(vector_list)}"
            )

        return vector_list

    def embed_query(self, text: str) -> List[float]:
        """Embed a single search query."""
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Cannot embed empty text query.")

        # If fastembed is loaded, compute locally in ~5ms
        if self._fastembed_model is not None:
            try:
                embeddings = list(self._fastembed_model.embed([clean_text]))
                return self._normalize_vector(embeddings[0])
            except Exception as e:
                logger.warning(f"FastEmbed query failed ({e}), attempting HTTP fallback.")

        # Fallback to Hugging Face router
        formatted_query = f"Represent this sentence for searching relevant passages: {clean_text}"
        return self._call_hf_api(formatted_query)

    def embed_document(self, text: str) -> List[float]:
        """Embed a single document chunk."""
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Cannot embed empty document text.")

        if self._fastembed_model is not None:
            try:
                embeddings = list(self._fastembed_model.embed([clean_text]))
                return self._normalize_vector(embeddings[0])
            except Exception as e:
                logger.warning(f"FastEmbed document embed failed ({e}), attempting HTTP fallback.")

        return self._call_hf_api(clean_text)

    def embed_documents(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        """Embed a batch of document chunks efficiently."""
        if not texts:
            return []

        if self._fastembed_model is not None:
            try:
                all_embeddings = list(self._fastembed_model.embed(texts, batch_size=batch_size))
                return [self._normalize_vector(emb) for emb in all_embeddings]
            except Exception as e:
                logger.warning(f"FastEmbed batch failed ({e}), falling back to iterative.")

        results: List[List[float]] = []
        for doc in texts:
            results.append(self.embed_document(doc))
        return results

    def _call_hf_api(self, text: str) -> List[float]:
        """Execute POST request to Hugging Face Inference API."""
        api_url = f"https://router.huggingface.co/hf-inference/models/{self.model_name}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {"inputs": text}

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(api_url, headers=headers, json=payload)

                if response.status_code == 200:
                    return self._normalize_vector(response.json())

                response.raise_for_status()

            except Exception as e:
                last_error = e
                logger.warning(f"HF API attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(1.0 * attempt)

        raise RuntimeError(f"Embedding generation failed: {last_error}")


# Global singleton instance for clean imports
embedding_client = EmbeddingClient()
