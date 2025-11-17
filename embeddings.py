"""
Embedding service for converting text to vector embeddings.
"""
import os
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(self, model_name: str = None):
        """
        Initialize the embedding service.

        Args:
            model_name: Name of the sentence-transformers model to use.
                       Defaults to value from environment or 'all-MiniLM-L6-v2'.
        """
        self.model_name = model_name or os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        print(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"Embedding dimension: {self.dimension}")

    def embed(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embeddings for text.

        Args:
            text: Single text string or list of text strings.

        Returns:
            numpy array of embeddings. Shape: (dimension,) for single text,
            or (n, dimension) for list of texts.
        """
        if isinstance(text, str):
            # Single text
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        else:
            # Multiple texts
            embeddings = self.model.encode(text, convert_to_numpy=True)
            return embeddings

    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a search query.

        Args:
            query: Query text.

        Returns:
            numpy array of shape (dimension,).
        """
        return self.embed(query)

    def embed_documents(self, documents: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple documents.

        Args:
            documents: List of document texts.

        Returns:
            numpy array of shape (n, dimension).
        """
        return self.embed(documents)

    def get_dimension(self) -> int:
        """Get the embedding dimension."""
        return self.dimension


# Singleton instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """
    Get or create the singleton embedding service instance.

    Returns:
        EmbeddingService instance.
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
