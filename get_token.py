# get_token.py
import requests
import os
from datetime import datetime

# From GitHub Secrets
API_KEY = os.getenv("UPSTOX_API_KEY")
API_SECRET = os.getenv("UPSTOX_API_SECRET")
REDIRECT_URI = "http://localhost"

# Step 1: Get auth code (manual once, then cached or use saved)
# For full automation, we use a **pre-obtained code** (run once locally)
# OR use Upstox's **API Key + Secret direct login** (not allowed)
# So we **store code in secret** and refresh token daily

def refresh_token():
    code = os.getenv("UPSTOX_AUTH_CODE")  # From first manual login
    if not code:
        print("Error: UPSTOX_AUTH_CODE missing")
        return None

    url = "https://api.upstox.com/v2/login/authorization/token"
    payload = {
        "code": code,
        "client_id": API_KEY,
        "client_secret": API_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    resp = requests.post(url, data=payload)
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        print(f"Token refreshed at {datetime.now().strftime('%H:%M')}")
        return token
    else:
        print(f"Token refresh failed: {resp.text}")
        return None

if __name__ == "__main__":
    token = refresh_token()
    if token:
        # Write to secrets.toml
        with open(".streamlit/secrets.toml", "w") as f:
            f.write(f"""[upstox]
api_key = "{API_KEY}"
api_secret = "{API_SECRET}"
access_token = "{token}"

[scanner]
unit = "minutes"
interval = "1"
lookback_bars = 100
rsi_period = 14
rsi_oversold = 30
rsi_overbought = 70
""")
        print("secrets.toml updated")
