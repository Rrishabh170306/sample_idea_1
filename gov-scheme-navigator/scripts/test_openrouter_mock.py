"""Simple test script that mocks OpenRouter responses for local testing.

Run with: `python scripts/test_openrouter_mock.py`
"""
from unittest.mock import patch
import json

from app.llm.client import LLMClient


def fake_post(*args, **kwargs):
    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "test response"}}]}

    return Resp()


def main():
    client = LLMClient()
    with patch("httpx.Client.post", side_effect=fake_post), patch("httpx.AsyncClient.post", side_effect=fake_post):
        resp = client.generate_sync("Hello world")
        print("Sync response:", resp)

    import asyncio

    async def run_async():
        async_client = LLMClient()
        resp = await async_client.generate("Hello async world")
        print("Async response:", resp)

    asyncio.run(run_async())


if __name__ == "__main__":
    main()
