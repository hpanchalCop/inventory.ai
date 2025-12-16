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
from shared.auth import require_auth, Auth0User, get_current_user
from shared.cloudwatch_stats import cloudwatch_stats

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


class TextSearchRequest(BaseModel):
    """Text-based search request schema."""
    query: str
    top_k: int = 5


class SimilaritySearchResponse(BaseModel):
    """Similarity search response schema."""
    product: ProductResponse
    similarity_score: float


@app.on_event("startup")
async def startup_event():
    """Initialize database and models on startup."""
    print("Starting Inventory.AI API...")
    try:
        init_db()
        print("✓ Database initialized")
    except Exception as e:
        print(f"⚠ Database initialization warning: {e}")
        print("  API will start but database operations may fail")
    print("✓ API startup complete")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Inventory.AI API",
        "version": "1.0.0",
        "endpoints": {
            "products": "/products",
            "search_text": "/search/text",
            "search_image": "/search/image",
            "search_multimodal": "/search/multimodal"
        }
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint with database connectivity test."""
    try:
        # Test database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        
        # Check ML models status
        ml_status = {
            "models_loaded": embedding_service._models_loaded,
            "multimodal_model": embedding_service.multimodal_model is not None,
            "text_model": embedding_service.text_model is not None
        }
        
        return {
            "status": "healthy", 
            "database": "connected",
            "ml_service": ml_status
        }
    except Exception as e:
        # Return 200 but indicate DB issue
        return {"status": "degraded", "database": "disconnected", "error": str(e)}


# =============================================================================
# ADMIN ENDPOINTS (No Auth Required)
# =============================================================================

@app.get("/admin/stats")
async def get_admin_stats():
    """
    Get API usage statistics from CloudWatch.
    
    Returns comprehensive statistics including:
    - Total requests by time period
    - Requests by endpoint
    - Requests by HTTP method
    - Response times
    - Error rates
    """
    stats = cloudwatch_stats.get_full_stats()
    return stats


@app.get("/admin/stats/summary")
async def get_stats_summary():
    """Get a quick summary of API usage."""
    stats = cloudwatch_stats.get_request_stats_from_logs(hours=24)
    return {
        "period": "last_24_hours",
        "total_requests": stats.get('total_requests', 0),
        "top_endpoints": dict(list(stats.get('by_endpoint', {}).items())[:5])
    }


# =============================================================================
# PROTECTED ENDPOINTS (Auth0 Required for POST/DELETE)
# =============================================================================

@app.post("/products/multipart", response_model=ProductResponse)
async def create_product_multipart(
    name: str = Form(...),
    description: str = Form(...),
    category: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Auth0User = Depends(get_current_user)
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
    db: Session = Depends(get_db),
    current_user: Auth0User = Depends(get_current_user)
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


@app.post("/search/text", response_model=List[SimilaritySearchResponse])
async def search_by_text(
    request: TextSearchRequest,
    db: Session = Depends(get_db),
    current_user: Auth0User = Depends(get_current_user)
):
    """
    Search for products using text query.
    
    Example: "bariatric wheelchair with reclining back"
    """
    try:
        # Generate embedding from query text
        query_embedding = embedding_service.generate_text_embedding(request.query)
        
        # Get all products with text embeddings
        all_products = db.query(Product).filter(
            Product.text_embedding.isnot(None)
        ).all()
        
        if not all_products:
            return []
        
        # Extract embeddings
        import numpy as np
        product_embeddings = [np.array(p.text_embedding) for p in all_products]
        query_embedding = np.array(query_embedding)
        
        # Find similar products
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
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.post("/search/image", response_model=List[SimilaritySearchResponse])
async def search_by_image(
    image: UploadFile = File(...),
    top_k: int = Form(5),
    db: Session = Depends(get_db),
    current_user: Auth0User = Depends(get_current_user)
):
    """
    Search for products by uploading an image.
    
    Upload a product image to find visually similar items.
    """
    try:
        # Read and process image
        contents = await image.read()
        pil_image = Image.open(io.BytesIO(contents))
        
        # Generate multimodal embedding from image only
        query_embedding = embedding_service.generate_multimodal_embedding("", pil_image)
        
        # Get all products with multimodal embeddings
        all_products = db.query(Product).filter(
            Product.multimodal_embedding.isnot(None)
        ).all()
        
        if not all_products:
            return []
        
        # Extract embeddings
        import numpy as np
        product_embeddings = [np.array(p.multimodal_embedding) for p in all_products]
        query_embedding = np.array(query_embedding)
        
        # Find similar products
        similar_indices = embedding_service.find_similar_products(
            query_embedding, product_embeddings, top_k
        )
        
        # Build response
        results = []
        for idx, similarity in similar_indices:
            results.append(SimilaritySearchResponse(
                product=all_products[idx],
                similarity_score=similarity
            ))
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.post("/search/multimodal", response_model=List[SimilaritySearchResponse])
async def search_multimodal(
    query: str = Form(...),
    image: Optional[UploadFile] = File(None),
    top_k: int = Form(5),
    db: Session = Depends(get_db),
    current_user: Auth0User = Depends(get_current_user)
):
    """
    Search for products using both text and image (multimodal).
    
    Combines text description with optional image for best results.
    Example: query="hospital bed" + image of a bed
    """
    try:
        # Process image if provided
        pil_image = None
        if image:
            contents = await image.read()
            pil_image = Image.open(io.BytesIO(contents))
        
        # Generate multimodal embedding
        query_embedding = embedding_service.generate_multimodal_embedding(query, pil_image)
        
        # Get all products with multimodal embeddings
        all_products = db.query(Product).filter(
            Product.multimodal_embedding.isnot(None)
        ).all()
        
        if not all_products:
            return []
        
        # Extract embeddings
        import numpy as np
        product_embeddings = [np.array(p.multimodal_embedding) for p in all_products]
        query_embedding = np.array(query_embedding)
        
        # Find similar products
        similar_indices = embedding_service.find_similar_products(
            query_embedding, product_embeddings, top_k
        )
        
        # Build response
        results = []
        for idx, similarity in similar_indices:
            results.append(SimilaritySearchResponse(
                product=all_products[idx],
                similarity_score=similarity
            ))
        
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@app.delete("/products/{product_id}")
async def delete_product(
    product_id: int, 
    db: Session = Depends(get_db),
    current_user: Auth0User = Depends(get_current_user)
):
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
