import os
import requests
import asyncio
from typing import Any, Dict, List

SERPER_URL = "https://google.serper.dev/search"


def search_product(query: str) -> Dict[str, Any]:
    """
    Debug/helper: returns the full Serper JSON response.
    This can raise if the key is missing or request fails.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise RuntimeError("SERPER_API_KEY not set")

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    payload = {"q": query, "num": 5}

    response = requests.post(SERPER_URL, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


async def serper_search(query: str) -> List[Dict[str, Any]]:
    """
    Used by the agents.
    Returns ONLY the list of organic results (list of dicts).
    On any failure, returns [] so downstream code won't crash.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return []

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    payload = {"q": query, "num": 5}

    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(SERPER_URL, json=payload, headers=headers, timeout=30),
        )
        response.raise_for_status()
        data = response.json()

        organic = data.get("organic", [])
        return organic if isinstance(organic, list) else []
    except Exception as e:
        print(f"[serper_search] failed for query={query!r}: {e}")
        return []
