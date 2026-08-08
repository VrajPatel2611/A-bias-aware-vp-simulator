"""
test_api.py
-----------
Quick connectivity check for the Groq API key.

Run this BEFORE a testing session to confirm the key works, so you do not
discover a bad key halfway through a participant's consultation.

Usage:  python test_api.py
"""

import os
import sys
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

if not api_key or api_key.startswith("your-"):
    print("FAIL: GROQ_API_KEY is not set in .env")
    print("      Get a free key at https://console.groq.com/keys")
    sys.exit(1)

print(f"Testing model: {model}")

try:
    client = Groq(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system",
             "content": "You are a patient in a clinical simulation. "
                        "Reply in one short sentence."},
            {"role": "user", "content": "Hello, what brings you in today?"},
        ],
        max_tokens=60,
        temperature=0.7,
    )
    reply = (resp.choices[0].message.content or "").strip()
    if not reply:
        print("FAIL: model returned an empty response")
        sys.exit(1)
    print(f"OK: API is working.\n    Patient replied: {reply}")

except Exception as e:
    print(f"FAIL: {e}")
    if "401" in str(e) or "invalid" in str(e).lower():
        print("      The key appears to be invalid — check .env")
    elif "429" in str(e):
        print("      Rate limited — wait a moment and retry")
    elif "model" in str(e).lower():
        print(f"      Model '{model}' may not exist. "
              f"Try GROQ_MODEL=llama-3.1-8b-instant in .env")
    sys.exit(1)
