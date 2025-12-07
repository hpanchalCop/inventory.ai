"""Tests for the FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.main import app
from shared.database import Base, get_db

# Test database
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override dependency
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Set up test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_create_product_text_only():
    """Test creating a product with text only."""
    product_data = {
        "name": "Test Product",
        "description": "This is a test product description",
        "category": "Test Category",
        "price": 29.99
    }
    
    response = client.post("/products/text-only", json=product_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == product_data["name"]
    assert data["description"] == product_data["description"]
    assert data["category"] == product_data["category"]
    assert "id" in data


def test_list_products():
    """Test listing products."""
    # First create a product
    product_data = {
        "name": "Test Product",
        "description": "Test description",
        "category": "Test",
        "price": 10.0
    }
    client.post("/products/text-only", json=product_data)
    
    # List products
    response = client.get("/products")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_product():
    """Test getting a specific product."""
    # Create a product first
    product_data = {
        "name": "Test Product",
        "description": "Test description",
        "category": "Test",
        "price": 10.0
    }
    create_response = client.post("/products/text-only", json=product_data)
    product_id = create_response.json()["id"]
    
    # Get the product
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == product_id
    assert data["name"] == product_data["name"]


def test_get_nonexistent_product():
    """Test getting a product that doesn't exist."""
    response = client.get("/products/9999")
    assert response.status_code == 404


def test_delete_product():
    """Test deleting a product."""
    # Create a product first
    product_data = {
        "name": "Test Product",
        "description": "Test description",
        "category": "Test",
        "price": 10.0
    }
    create_response = client.post("/products/text-only", json=product_data)
    product_id = create_response.json()["id"]
    
    # Delete the product
    response = client.delete(f"/products/{product_id}")
    assert response.status_code == 200
    
    # Verify it's deleted
    get_response = client.get(f"/products/{product_id}")
    assert get_response.status_code == 404
