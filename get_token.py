# get_token.py
from upstox_client import Auth
import os

API_KEY = "your_api_key"  # From Upstox console
API_SECRET = "your_api_secret"
REDIRECT_URI = "http://localhost"

auth = Auth()
print("Step 1: Open this URL in browser & login:")
url = auth.get_authorization_url(API_KEY, REDIRECT_URI)
print(url)
print("\nStep 2: After redirect, copy 'code' from URL (e.g., http://localhost?code=ABC123)")

code = input("Paste code: ")
token = auth.get_access_token(API_KEY, API_SECRET, code, REDIRECT_URI)

# Save to secrets.toml or env
with open(".streamlit/secrets.toml", "a") as f:
    f.write(f'\naccess_token = "{token}"\n')

print(f"\nSuccess! access_token: {token}")
print("Update secrets.toml and restart your scanner.")
