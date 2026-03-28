"""
Semantic deduplication module for Homeschool.
Uses embeddings to detect and skip similar flashcards.
"""

import os
from typing import Optional, List, Tuple
from pathlib import Path

from .logging import get_logger

logger = get_logger(__name__)


class SemanticDeduplicator:
    """Detects semantically similar flashcards using embeddings."""

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        embedder=None,
        chroma_client=None,
        collection_name: str = "homeschool"
    ):
        """
        Initialize the semantic deduplicator.
        
        Args:
            similarity_threshold: Minimum similarity to consider cards duplicate (0-1)
            embedder: Sentence transformer or similar embedder
            chroma_client: ChromaDB client instance
            collection_name: Name of the collection to check against
        """
        self.similarity_threshold = similarity_threshold
        self.embedder = embedder
        self.chroma_client = chroma_client
        self.collection_name = collection_name
        self._collection = None

    def _get_collection(self):
        """Get or cached ChromaDB collection."""
        if self.chroma_client and self._collection is None:
            try:
                self._collection = self.chroma_client.get_or_create_collection(
                    name=self.collection_name
                )
            except Exception as e:
                logger.warning("Could not get ChromaDB collection", error=str(e))
        return self._collection

    def compute_embedding(self, text: str) -> Optional[List[float]]:
        """Compute embedding for given text."""
        if self.embedder:
            try:
                embedding = self.embedder.encode([text])[0].tolist()
                return embedding
            except Exception as e:
                logger.error("Failed to compute embedding", error=str(e))
        return None

    def check_similarity(self, text: str) -> Tuple[bool, float, Optional[str]]:
        """
        Check if text is semantically similar to existing cards.
        
        Args:
            text: Text to check (e.g., "Question: What is X? Answer: Y")
            
        Returns:
            Tuple of (is_duplicate, similarity_score, existing_card_id)
        """
        embedding = self.compute_embedding(text)
        if not embedding or not self._get_collection():
            return False, 0.0, None

        try:
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=1
            )
            
            if results and results.get("ids") and results["ids"][0]:
                existing_id = results["ids"][0][0]
                # Note: ChromaDB doesn't return similarity scores by default
                # but the distance can be used to compute similarity
                # For cosine distance: similarity = 1 - distance
                distance = results.get("distances", [[1.0]])[0][0]
                
                if distance < 0.15:  # Very similar (distance ~0.15 means ~85% similar)
                    return True, 1 - distance, existing_id
                    
        except Exception as e:
            logger.error("Failed to query for similarity", error=str(e))
        
        return False, 0.0, None

    def should_skip_card(self, question: str, answer: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if a card should be skipped due to semantic similarity.
        
        Args:
            question: Flashcard question
            answer: Flashcard answer
            
        Returns:
            Tuple of (should_skip, existing_card_id)
        """
        text_to_check = f"Question: {question} Answer: {answer}"
        
        is_duplicate, similarity, existing_id = self.check_similarity(text_to_check)
        
        if is_duplicate:
            logger.info(
                "Skipping duplicate card",
                similarity=similarity,
                existing_id=existing_id,
                question=question[:50] + "..." if len(question) > 50 else question
            )
            
        return is_duplicate, existing_id


def create_deduplicator(
    config,
    chroma_client=None,
    similarity_threshold: Optional[float] = None
) -> SemanticDeduplicator:
    """
    Factory function to create a SemanticDeduplicator from config.
    
    Args:
        config: Homeschool Config object
        chroma_client: Optional ChromaDB client
        similarity_threshold: Optional override for threshold
        
    Returns:
        Configured SemanticDeduplicator instance
    """
    from .config import load
    
    # Get threshold from config or use default
    threshold = similarity_threshold or getattr(config, 'deduplication', {}).get(
        'similarity_threshold', 0.85
    )
    
    embedder = None
    # Try to use sentence-transformers if available
    try:
        from sentence_transformers import SentenceTransformer
        embedder = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Initialized sentence transformer for deduplication")
    except ImportError:
        logger.warning("sentence-transformers not available, deduplication limited")
    
    return SemanticDeduplicator(
        similarity_threshold=threshold,
        embedder=embedder,
        chroma_client=chroma_client,
        collection_name=config.chromadb.collection_name
    )
