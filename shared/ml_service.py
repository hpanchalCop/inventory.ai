"""ML services for generating embeddings."""
from typing import Optional, List
import numpy as np
from PIL import Image
from io import BytesIO
from sentence_transformers import SentenceTransformer
import torch

from shared.config import settings


class EmbeddingService:
    """Service for generating multimodal and text embeddings."""
    
    def __init__(self):
        """Initialize embedding models."""
        self.multimodal_model = None
        self.text_model = None
        self._load_models()
    
    def _load_models(self):
        """Load embedding models."""
        try:
            # Load CLIP model for multimodal embeddings
            self.multimodal_model = SentenceTransformer(settings.embedding_model)
            
            # Load text-only model for fallback
            self.text_model = SentenceTransformer(settings.text_embedding_model)
            
            print("Embedding models loaded successfully")
        except Exception as e:
            print(f"Error loading embedding models: {e}")
    
    def generate_multimodal_embedding(
        self, 
        text: str, 
        image: Optional[Image.Image] = None
    ) -> Optional[np.ndarray]:
        """
        Generate multimodal embedding from text and image.
        
        Args:
            text: Product description
            image: Product image (PIL Image)
            
        Returns:
            Embedding vector or None if failed
        """
        try:
            if image is not None and self.multimodal_model:
                # For CLIP, we encode text and image separately then combine
                text_features = self.multimodal_model.encode(text, convert_to_tensor=True)
                image_features = self.multimodal_model.encode(image, convert_to_tensor=True)
                
                # Average the features
                combined = (text_features + image_features) / 2
                return combined.cpu().numpy()
            elif self.multimodal_model:
                # Text only with multimodal model
                features = self.multimodal_model.encode(text)
                return features
            return None
        except Exception as e:
            print(f"Error generating multimodal embedding: {e}")
            return None
    
    def generate_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Generate text-only embedding (fallback).
        
        Args:
            text: Product description
            
        Returns:
            Embedding vector or None if failed
        """
        try:
            if self.text_model:
                features = self.text_model.encode(text)
                return features
            return None
        except Exception as e:
            print(f"Error generating text embedding: {e}")
            return None
    
    def compute_similarity(
        self, 
        embedding1: np.ndarray, 
        embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score (0-1)
        """
        try:
            # Normalize vectors
            norm1 = embedding1 / np.linalg.norm(embedding1)
            norm2 = embedding2 / np.linalg.norm(embedding2)
            
            # Compute cosine similarity
            similarity = np.dot(norm1, norm2)
            return float(similarity)
        except Exception as e:
            print(f"Error computing similarity: {e}")
            return 0.0
    
    def find_similar_products(
        self, 
        query_embedding: np.ndarray,
        product_embeddings: List[np.ndarray],
        top_k: int = 5
    ) -> List[tuple]:
        """
        Find most similar products based on embeddings.
        
        Args:
            query_embedding: Query product embedding
            product_embeddings: List of product embeddings
            top_k: Number of results to return
            
        Returns:
            List of (index, similarity_score) tuples
        """
        similarities = []
        for idx, prod_embedding in enumerate(product_embeddings):
            similarity = self.compute_similarity(query_embedding, prod_embedding)
            similarities.append((idx, similarity))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


# Singleton instance
embedding_service = EmbeddingService()
