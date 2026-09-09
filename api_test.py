# =============================================================================
# api_test.py  —  Quick Gemini API connectivity & model check
# =============================================================================
# Usage:
#   $env:GEMINI_API_KEY = "AIza..."   # paste your key here in terminal
#   python api_test.py
# =============================================================================

import os
import sys
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    print("ERROR: GEMINI_API_KEY is not set.")
    print("Run:  $env:GEMINI_API_KEY = 'AIza...'  then try again.")
    sys.exit(1)

print(f"Key loaded: {api_key[:8]}...{api_key[-4:]}  (length: {len(api_key)})")
print()

from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)

# ------------------------------------------------------------------
# Test 1: List available models (checks auth + connectivity)
# ------------------------------------------------------------------
print("=" * 55)
print("TEST 1: List Gemini models accessible with this key")
print("=" * 55)
try:
    models = client.models.list()
    flash_models = [m.name for m in models if "flash" in m.name.lower()]
    print(f"Flash models available ({len(flash_models)}):")
    for m in flash_models:
        print(f"  • {m}")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)

# ------------------------------------------------------------------
# Test 2: Simple generation with gemini-2.5-flash (fallback)
# ------------------------------------------------------------------
print()
print("=" * 55)
print("TEST 2: Simple text generation (gemini-2.5-flash)")
print("=" * 55)
try:
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Reply with exactly: API connection successful",
        config=types.GenerateContentConfig(temperature=0.0)
    )
    print(f"Response: {resp.text.strip()}")
    print("STATUS: PASS ✓")
except Exception as e:
    print(f"FAILED: {e}")

# ------------------------------------------------------------------
# Test 3: Try gemini-3.6-flash specifically
# ------------------------------------------------------------------
print()
print("=" * 55)
print("TEST 3: Test gemini-3.6-flash (pipeline model)")
print("=" * 55)
try:
    resp = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Reply with exactly: gemini-3.6-flash is live",
        config=types.GenerateContentConfig(temperature=0.0)
    )
    print(f"Response: {resp.text.strip()}")
    print("STATUS: PASS ✓  — gemini-3.6-flash is accessible!")
except Exception as e:
    print(f"STATUS: FAIL ✗  — {e}")
    print("Fallback: Update MODEL_ID in processor.py to 'gemini-2.5-flash'")

print()
print("Done.")
