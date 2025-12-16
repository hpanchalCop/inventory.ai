"""Quick script to get Auth0 token for Swagger."""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

response = requests.post(
    f"https://{os.getenv('AUTH0_DOMAIN')}/oauth/token",
    json={
        'client_id': os.getenv('AUTH0_CLIENT_ID'),
        'client_secret': os.getenv('AUTH0_CLIENT_SECRET'),
        'audience': os.getenv('AUTH0_API_AUDIENCE'),
        'grant_type': 'client_credentials'
    }
)

if response.status_code == 200:
    token = response.json()['access_token']
    print(token)
else:
    print(f"Error: {response.status_code}")
    print(response.text)
