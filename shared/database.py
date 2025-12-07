"""Database models and setup."""
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pgvector.sqlalchemy import Vector

from shared.config import settings

Base = declarative_base()


class Product(Base):
    """Product model with embeddings support."""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    image_url = Column(String(512), nullable=True)
    s3_key = Column(String(512), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    price = Column(Float, nullable=True)
    
    # Embeddings - 512 dimensions for CLIP
    multimodal_embedding = Column(Vector(512), nullable=True)
    text_embedding = Column(Vector(384), nullable=True)  # 384 for all-MiniLM-L6-v2
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
