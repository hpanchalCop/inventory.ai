"""Test script for search endpoints."""
import requests
import os
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

# Test text search
def test_text_search(query="beds", top_k=5):
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(
        "http://localhost:8000/search/text",
        json={"query": query, "top_k": top_k},
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    print(f"Query: '{query}'")
    print(f"\nResults ({len(response.json())} products):")
    print("=" * 80)
    
    for result in response.json():
        product = result['product']
        score = result['similarity_score']
        print(f"\n✓ {product['name']} (Similarity: {score:.3f})")
        print(f"  Category: {product['category']}")
        print(f"  Price: ${product['price']:.2f}")
        print(f"  Description: {product['description'][:100]}...")
    
    return response.json()

if __name__ == "__main__":
    print("Testing Text Search Endpoint")
    print("=" * 80)
    test_text_search("hospital beds with adjustable height", top_k=5)
