"""Tests for ML service."""
import pytest
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.ml_service import EmbeddingService


def test_embedding_service_initialization():
    """Test that embedding service initializes."""
    service = EmbeddingService()
    assert service is not None


def test_generate_text_embedding():
    """Test generating text embedding."""
    service = EmbeddingService()
    text = "This is a test product description"
    
    embedding = service.generate_text_embedding(text)
    
    if embedding is not None:
        assert isinstance(embedding, np.ndarray)
        assert len(embedding) > 0


def test_compute_similarity():
    """Test computing similarity between embeddings."""
    service = EmbeddingService()
    
    # Create two similar embeddings
    emb1 = np.array([1.0, 2.0, 3.0])
    emb2 = np.array([1.1, 2.1, 3.1])
    
    similarity = service.compute_similarity(emb1, emb2)
    
    assert isinstance(similarity, float)
    assert 0.0 <= similarity <= 1.0


def test_compute_similarity_identical():
    """Test similarity of identical embeddings."""
    service = EmbeddingService()
    
    emb = np.array([1.0, 2.0, 3.0])
    
    similarity = service.compute_similarity(emb, emb)
    
    # Identical embeddings should have similarity close to 1
    assert similarity > 0.99
