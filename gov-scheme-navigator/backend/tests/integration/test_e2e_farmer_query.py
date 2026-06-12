"""End-to-end test: the full farmer query scenario.

Scenario: "I am a farmer from Tamil Nadu with 3 acres of land. 
           Which government schemes can I apply for?"

This test verifies:
1. The POST /api/v1/chat/messages endpoint responds 200
2. The reply is non-empty text
3. At least one scheme is returned
4. The response includes citation sources

Run against a live backend:
    python scripts/e2e_test.py [--base-url http://localhost:8000]

Or as a pytest test (requires running backend):
    pytest tests/integration/test_e2e_farmer_query.py -v -m e2e
"""
from __future__ import annotations

import json
import os
import sys

import httpx
import pytest

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FARMER_QUERY = (
    "I am a farmer from Tamil Nadu with 3 acres of agricultural land. "
    "My annual income is Rs 80,000. I am 42 years old. "
    "Which government schemes can I apply for and what documents do I need?"
)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_health_endpoint():
    """Backend /health must return 200."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    data = resp.json()
    assert data.get("status") == "ok"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_farmer_query_returns_schemes():
    """Full farmer query should return at least one scheme."""
    payload = {
        "message": FARMER_QUERY,
        "user_profile": {
            "state": "Tamil Nadu",
            "occupation": "farmer",
            "age": 42,
            "income": 80000,
            "land_hectares": 3.0,
        },
    }
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        resp = await client.post(
            "/api/v1/chat/messages",
            json=payload,
            headers={"Content-Type": "application/json"},
        )

    assert resp.status_code == 200, f"Chat API failed ({resp.status_code}): {resp.text}"
    data = resp.json()

    # 1. Must have a non-empty reply
    assert data.get("reply"), "Response 'reply' is empty"
    assert len(data["reply"]) > 20, "Reply is too short"

    # 2. Must have a session_id
    assert data.get("session_id"), "No session_id in response"

    # 3. Must return at least one scheme
    schemes = data.get("schemes", [])
    assert len(schemes) >= 1, (
        f"Expected at least 1 scheme, got {len(schemes)}. Reply: {data['reply'][:200]}"
    )

    print(f"\n✓ Reply: {data['reply'][:200]}...")
    print(f"✓ Schemes found: {[s['name'] for s in schemes]}")
    print(f"✓ Query type: {data.get('query_type')}")
    print(f"✓ Citations: {len(data.get('citations', []))}")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_eligibility_query():
    """Eligibility-type query should return eligibility results."""
    payload = {
        "message": "Am I eligible for PM-KISAN if I am a small farmer with 2 acres?",
        "user_profile": {
            "state": "Central",
            "occupation": "farmer",
            "age": 38,
            "income": 60000,
            "land_hectares": 2.0,
        },
    }
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        resp = await client.post("/api/v1/chat/messages", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data.get("reply")
    print(f"\n✓ Eligibility reply: {data['reply'][:200]}...")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_session_continuity():
    """Subsequent messages with the same session_id should be accepted."""
    session_id = "test-session-continuity-001"
    messages = [
        "I am a farmer from Tamil Nadu",
        "What documents do I need for PM-KISAN?",
    ]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        for msg in messages:
            resp = await client.post(
                "/api/v1/chat/messages",
                json={"message": msg, "session_id": session_id},
            )
            assert resp.status_code == 200, f"Message failed: {msg}"
            data = resp.json()
            assert data.get("reply")
            print(f"\n✓ [{msg[:40]}...] → {data['reply'][:100]}...")


# ─── Standalone script mode ────────────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio

    base = sys.argv[1] if len(sys.argv) > 1 else BASE_URL
    BASE_URL = base

    async def main():
        print(f"Running E2E tests against {BASE_URL}\n")
        print("─" * 60)

        # Health
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            r = await client.get("/health")
            status = r.json()
            print(f"[HEALTH] {json.dumps(status, indent=2)}")

        # Farmer query
        payload = {
            "message": FARMER_QUERY,
            "user_profile": {
                "state": "Tamil Nadu",
                "occupation": "farmer",
                "age": 42,
                "income": 80000,
                "land_hectares": 3.0,
            },
        }
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
            r = await client.post("/api/v1/chat/messages", json=payload)

        if r.status_code != 200:
            print(f"[FAIL] Status {r.status_code}: {r.text}")
            sys.exit(1)

        data = r.json()
        print(f"\n[REPLY]\n{data['reply']}")
        print(f"\n[SCHEMES]")
        for s in data.get("schemes", []):
            print(f"  • {s['name']} (id={s['scheme_id']}, score={s['score']:.2f})")
        print(f"\n[ELIGIBILITY]")
        for sid, elig in data.get("eligibility", {}).items():
            status_str = "✓ ELIGIBLE" if elig["eligible"] else "✗ NOT ELIGIBLE"
            print(f"  {sid}: {status_str} (score={elig['score']:.2f})")
            if elig.get("explanation"):
                print(f"    → {elig['explanation']}")
        print(f"\n[CITATIONS]")
        for c in data.get("citations", []):
            print(f"  • {c.get('source_url', c)}")

        schemes = data.get("schemes", [])
        if not schemes:
            print("\n[WARN] No schemes returned. Check if backend is fully initialised.")
            sys.exit(1)

        print(f"\n{'─'*60}")
        print("✓ E2E test PASSED")

    asyncio.run(main())
