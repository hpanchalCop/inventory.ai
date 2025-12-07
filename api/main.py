"""FastAPI application for inventory.ai."""
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from PIL import Image
import io
import uuid
from datetime import datetime

from shared.database import init_db, get_db, Product
from shared.ml_service import embedding_service
from shared.s3_service import s3_service
from shared.config import settings

# Initialize FastAPI app
app = FastAPI(
    title="Inventory.AI API",
    description="FastAPI microservice for product inventory with multimodal embeddings",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class ProductCreate(BaseModel):
    """Product creation schema."""
    name: str
    description: str
    category: Optional[str] = None
    price: Optional[float] = None


class ProductResponse(BaseModel):
    """Product response schema."""
    id: int
    name: str
    description: str
    image_url: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class SimilaritySearchRequest(BaseModel):
    """Similarity search request schema."""
    product_id: int
    top_k: int = 5
    use_multimodal: bool = True


class SimilaritySearchResponse(BaseModel):
    """Similarity search response schema."""
    product: ProductResponse
    similarity_score: float


@app.on_event("startup")
async def startup_event():
    """Initialize database and models on startup."""
    init_db()
    print("Database initialized")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Inventory.AI API",
        "version": "1.0.0",
        "endpoints": {
            "products": "/products",
            "search": "/search/similar"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/products/multipart", response_model=ProductResponse)
async def create_product_multipart(
    name: str = Form(...),
    description: str = Form(...),
    category: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Create product with multipart request (image + text).
    
    Supports:
    - Image + text (multimodal embeddings)
    - Text only (text embeddings as fallback)
    """
    try:
        # Process image if provided
        pil_image = None
        image_url = None
        s3_key = None
        
        if image:
            # Read and validate image
            contents = await image.read()
            pil_image = Image.open(io.BytesIO(contents))
            
            # Upload to S3
            s3_key = f"products/{uuid.uuid4()}.jpg"
            image_url = s3_service.upload_image(pil_image, s3_key)
        
        # Generate embeddings
        multimodal_embedding = None
        text_embedding = None
        
        if pil_image:
            # Multimodal embedding (image + text)
            multimodal_embedding = embedding_service.generate_multimodal_embedding(
                description, pil_image
            )
        else:
            # Multimodal embedding with text only
            multimodal_embedding = embedding_service.generate_multimodal_embedding(
                description, None
            )
        
        # Always generate text-only embedding as fallback
        text_embedding = embedding_service.generate_text_embedding(description)
        
        # Create product in database
        product = Product(
            name=name,
            description=description,
            category=category,
            price=price,
            image_url=image_url,
            s3_key=s3_key,
            multimodal_embedding=multimodal_embedding.tolist() if multimodal_embedding is not None else None,
            text_embedding=text_embedding.tolist() if text_embedding is not None else None
        )
        
        db.add(product)
        db.commit()
        db.refresh(product)
        
        return product
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating product: {str(e)}")


@app.post("/products/text-only", response_model=ProductResponse)
async def create_product_text_only(
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    """
    Create product with text-only description.
    
    Uses text embeddings for semantic similarity.
    """
    try:
        # Generate text-only embeddings
        multimodal_embedding = embedding_service.generate_multimodal_embedding(
            product.description, None
        )
        text_embedding = embedding_service.generate_text_embedding(product.description)
        
        # Create product in database
        db_product = Product(
            name=product.name,
            description=product.description,
            category=product.category,
            price=product.price,
            multimodal_embedding=multimodal_embedding.tolist() if multimodal_embedding is not None else None,
            text_embedding=text_embedding.tolist() if text_embedding is not None else None
        )
        
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        
        return db_product
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating product: {str(e)}")


@app.get("/products", response_model=List[ProductResponse])
async def list_products(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all products with optional filtering."""
    query = db.query(Product)
    
    if category:
        query = query.filter(Product.category == category)
    
    products = query.offset(skip).limit(limit).all()
    return products


@app.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a specific product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@app.post("/search/similar", response_model=List[SimilaritySearchResponse])
async def search_similar_products(
    request: SimilaritySearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search for similar products using embeddings.
    
    Supports:
    - Multimodal similarity (if available)
    - Text-only similarity as fallback
    """
    # Get the query product
    query_product = db.query(Product).filter(Product.id == request.product_id).first()
    
    if not query_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Determine which embedding to use
    use_multimodal = request.use_multimodal and query_product.multimodal_embedding is not None
    
    if use_multimodal:
        query_embedding = query_product.multimodal_embedding
        # Get all products with multimodal embeddings
        all_products = db.query(Product).filter(
            Product.id != request.product_id,
            Product.multimodal_embedding.isnot(None)
        ).all()
        product_embeddings = [p.multimodal_embedding for p in all_products]
    else:
        # Fallback to text embeddings
        query_embedding = query_product.text_embedding
        if query_embedding is None:
            raise HTTPException(status_code=400, detail="Product has no embeddings")
        
        all_products = db.query(Product).filter(
            Product.id != request.product_id,
            Product.text_embedding.isnot(None)
        ).all()
        product_embeddings = [p.text_embedding for p in all_products]
    
    if not product_embeddings:
        return []
    
    # Find similar products
    import numpy as np
    query_embedding = np.array(query_embedding)
    product_embeddings = [np.array(emb) for emb in product_embeddings]
    
    similar_indices = embedding_service.find_similar_products(
        query_embedding, product_embeddings, request.top_k
    )
    
    # Build response
    results = []
    for idx, similarity in similar_indices:
        results.append(SimilaritySearchResponse(
            product=all_products[idx],
            similarity_score=similarity
        ))
    
    return results


@app.delete("/products/{product_id}")
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete a product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Delete image from S3 if exists
    if product.s3_key:
        s3_service.delete_image(product.s3_key)
    
    db.delete(product)
    db.commit()
    
    return {"message": "Product deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port
    )
