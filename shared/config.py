"""Configuration module for loading environment variables."""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/inventory_db"
    
    # AWS
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "inventory-ai-bucket"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Dashboard
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8050
    
    # ML Models
    embedding_model: str = "sentence-transformers/clip-ViT-B-32"
    text_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
