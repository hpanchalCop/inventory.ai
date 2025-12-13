"""Configuration module for loading environment variables."""
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
    
    # Auth0
    auth0_domain: str = "your-tenant.auth0.com"
    auth0_api_audience: str = "https://inventory-ai-api"
    auth0_algorithms: str = "RS256"
    auth0_client_id: str = "YOUR_AUTH0_CLIENT_ID"
    
    # CloudWatch
    cloudwatch_log_group: str = "/ecs/inventory-ai-api"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
