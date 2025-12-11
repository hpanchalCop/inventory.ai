"""Configuration module for loading environment variables."""
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    # Default local development DB (convenient fallback).
    # IMPORTANT: This default is intended for local development only.
    # When deploying to AWS (RDS), set the `DATABASE_URL` environment
    # variable (or update `.env`) to point to your RDS Postgres endpoint
    # with the appropriate credentials. Do NOT commit production credentials
    # into source control.
    database_url: str = "postgresql://postgres:postgres@localhost:5432/inventory_db"
    
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
