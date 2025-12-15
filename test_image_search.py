"""Test script for image-based search endpoints."""
import requests
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Get Auth0 token
def get_token():
    response = requests.post(
        f"https://{os.getenv('AUTH0_DOMAIN')}/oauth/token",
        json={
            'client_id': os.getenv('AUTH0_CLIENT_ID'),
            'client_secret': os.getenv('AUTH0_CLIENT_SECRET'),
            'audience': os.getenv('AUTH0_API_AUDIENCE'),
            'grant_type': 'client_credentials'
        }
    )
    return response.json()['access_token']


def test_image_search(image_path, top_k=5):
    """Test image-only search with uploaded image file."""
    print("\n" + "="*80)
    print("Testing Image Search Endpoint")
    print("="*80)
    print(f"Image: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return
    
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Upload image
    with open(image_path, 'rb') as img_file:
        files = {'image': (os.path.basename(image_path), img_file, 'image/jpeg')}
        data = {'top_k': top_k}
        
        response = requests.post(
            "http://localhost:8000/search/image",
            files=files,
            data=data,
            headers=headers
        )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        results = response.json()
        print(f"\nResults ({len(results)} products):")
        print("="*80)
        
        for result in results:
            product = result['product']
            score = result['similarity_score']
            print(f"\n✓ {product['name']} (Similarity: {score:.3f})")
            print(f"  Category: {product['category']}")
            print(f"  Price: ${product['price']:.2f}")
            print(f"  Description: {product['description'][:80]}...")
    else:
        print(f"Error: {response.text}")


def test_multimodal_search(image_path, query, top_k=5):
    """Test combined text + image search."""
    print("\n" + "="*80)
    print("Testing Multimodal Search Endpoint (Text + Image)")
    print("="*80)
    print(f"Image: {image_path}")
    print(f"Query: '{query}'")
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return
    
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Upload image with text query
    with open(image_path, 'rb') as img_file:
        files = {'image': (os.path.basename(image_path), img_file, 'image/jpeg')}
        data = {
            'query': query,
            'top_k': top_k
        }
        
        response = requests.post(
            "http://localhost:8000/search/multimodal",
            files=files,
            data=data,
            headers=headers
        )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        results = response.json()
        print(f"\nResults ({len(results)} products):")
        print("="*80)
        
        for result in results:
            product = result['product']
            score = result['similarity_score']
            print(f"\n✓ {product['name']} (Similarity: {score:.3f})")
            print(f"  Category: {product['category']}")
            print(f"  Price: ${product['price']:.2f}")
    else:
        print(f"Error: {response.text}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Image search:      python test_image_search.py <image_path>")
        print("  Multimodal search: python test_image_search.py <image_path> <query>")
        print("\nExamples:")
        print("  python test_image_search.py wheelchair.jpg")
        print("  python test_image_search.py wheelchair.jpg 'bariatric wheelchair for heavy patients'")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if len(sys.argv) >= 3:
        # Multimodal search with text query
        query = sys.argv[2]
        test_multimodal_search(image_path, query, top_k=5)
    else:
        # Image-only search
        test_image_search(image_path, top_k=5)
