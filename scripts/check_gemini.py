#!/usr/bin/env python3
"""
AtmoSync Gemini API Key & Model Diagnostic Tool
Safely checks API key formatting, active model availability, and latency without logging secrets.
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Search and load root or local .env
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "rag_pipeline" / ".env")


def mask_key(key: str | None) -> str:
    if not key:
        return "[MISSING]"
    if len(key) <= 8:
        return "****"
    return f"{key[:6]}...{key[-4:]}"


def main():
    print("=" * 65)
    print("AtmoSync Gemini Diagnostic Tool")
    print("=" * 65)

    api_key = os.getenv("GEMINI_API_KEY")
    provider = os.getenv("LLM_PROVIDER", "gemini")

    print(f"Configured LLM_PROVIDER: {provider}")
    print(f"Masked GEMINI_API_KEY:   {mask_key(api_key)}")

    if not api_key:
        print("\n[FAIL] GEMINI_API_KEY is not set in environment or .env file.")
        print("Tip: Add GEMINI_API_KEY=AIzaSy... to your root .env file, or set LLM_PROVIDER=mock for offline development.")
        sys.exit(1)

    if not api_key.startswith("AIzaSy"):
        print("\n[WARN] API key does not start with standard prefix 'AIzaSy'. Verify format.")
    else:
        print("[OK] API key format matches Google AI Studio signature.")

    try:
        from google import genai
        from google.genai import errors
    except ImportError:
        print("\n[FAIL] 'google-genai' package is not installed.")
        print("Run: pip install google-genai")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    test_models = [
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
    ]

    print("\nProbing active Gemini models with scientific test prompt...")
    test_prompt = "State in one sentence what synoptic meteorology studies."

    any_success = False

    for model in test_models:
        print(f"\n--- Testing Model: {model} ---")
        start_time = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=model,
                contents=test_prompt,
            )
            elapsed = time.perf_counter() - start_time
            if response.text and response.text.strip():
                print(f"  [SUCCESS] Status: 200 OK | Latency: {elapsed:.2f}s")
                print(f"  Response: {response.text.strip()[:100]}...")
                any_success = True
            else:
                print(f"  [WARN] Response was empty from {model} ({elapsed:.2f}s).")
        except errors.APIError as exc:
            elapsed = time.perf_counter() - start_time
            code = getattr(exc, "code", getattr(exc, "status_code", "Error"))
            print(f"  [ERROR] Status: {code} ({elapsed:.2f}s)")
            print(f"  Message: {exc.message if hasattr(exc, 'message') else str(exc)}")
        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            print(f"  [ERROR] Unexpected error ({elapsed:.2f}s): {exc}")

    print("\n" + "=" * 65)
    if any_success:
        print("[PASS] Gemini integration is functional with active models!")
        sys.exit(0)
    else:
        print("[FAIL] All Gemini models failed. The offline MockProvider is active as fallback.")
        sys.exit(1)


if __name__ == "__main__":
    main()
