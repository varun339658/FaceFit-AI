"""
fix_token.py — Run this ONCE to regenerate token.json with correct Google Calendar scope.

Your current token.json has scope: "https://www.googleapis.com/auth/calendar"
Your code was requesting:           "https://www.googleapis.com/auth/calendar.events"
These don't match → invalid_scope error

This script regenerates token.json using the correct scope.

Run:  python fix_token.py
"""

from google_auth_oauthlib.flow import InstalledAppFlow
import os

# This MUST match the scope used in outfit_scheduler_service.py
SCOPES = ["https://www.googleapis.com/auth/calendar"]

creds_path = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
token_path = os.getenv("GOOGLE_TOKEN_JSON", "token.json")

print(f"📂 Using credentials: {creds_path}")
print(f"📂 Will write token to: {token_path}")
print("🌐 Opening browser for Google OAuth...")

flow  = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
creds = flow.run_local_server(port=0)

with open(token_path, "w") as f:
    f.write(creds.to_json())

print(f"✅ token.json regenerated successfully at: {token_path}")
print(f"   Scopes: {creds.scopes}")
print("   Restart your Flask server — Google Calendar will now work!")