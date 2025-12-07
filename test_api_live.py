#!/usr/bin/env python3
"""Simple API test script to verify the API is working."""
import requests
import json
import sys


def test_api():
    """Test basic API functionality."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing inventory.ai API\n")
    
    # Test 1: Health check
    print("1. Testing health check endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("   ✓ Health check passed")
        else:
            print(f"   ✗ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Health check failed: {e}")
        return False
    
    # Test 2: Root endpoint
    print("\n2. Testing root endpoint...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Root endpoint: {data['message']}")
        else:
            print(f"   ✗ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Root endpoint failed: {e}")
        return False
    
    # Test 3: Create a product
    print("\n3. Testing product creation...")
    product_data = {
        "name": "Test Product",
        "description": "This is a test product for API verification",
        "category": "Test",
        "price": 99.99
    }
    try:
        response = requests.post(
            f"{base_url}/products/text-only",
            json=product_data,
            timeout=10
        )
        if response.status_code == 200:
            created_product = response.json()
            product_id = created_product["id"]
            print(f"   ✓ Product created with ID: {product_id}")
        else:
            print(f"   ✗ Product creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ✗ Product creation failed: {e}")
        return False
    
    # Test 4: Get the product
    print("\n4. Testing product retrieval...")
    try:
        response = requests.get(f"{base_url}/products/{product_id}", timeout=5)
        if response.status_code == 200:
            product = response.json()
            print(f"   ✓ Retrieved product: {product['name']}")
        else:
            print(f"   ✗ Product retrieval failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Product retrieval failed: {e}")
        return False
    
    # Test 5: List products
    print("\n5. Testing product listing...")
    try:
        response = requests.get(f"{base_url}/products", timeout=5)
        if response.status_code == 200:
            products = response.json()
            print(f"   ✓ Found {len(products)} product(s)")
        else:
            print(f"   ✗ Product listing failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Product listing failed: {e}")
        return False
    
    # Test 6: Delete the product
    print("\n6. Testing product deletion...")
    try:
        response = requests.delete(f"{base_url}/products/{product_id}", timeout=5)
        if response.status_code == 200:
            print(f"   ✓ Product deleted successfully")
        else:
            print(f"   ✗ Product deletion failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Product deletion failed: {e}")
        return False
    
    print("\n✅ All API tests passed!")
    return True


if __name__ == "__main__":
    try:
        success = test_api()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
