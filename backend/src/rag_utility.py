import asyncio
import json
import os
import urllib.parse
import urllib.request
from typing import Any, Optional

# Environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

LOCAL_ADVISORIES_PATH = os.path.join(os.path.dirname(__file__), "local_advisories.json")

# In-memory cache for advisories dataset
_LOCAL_ADVISORIES_CACHE: Optional[list[dict[str, Any]]] = None


def _load_local_advisories() -> list[dict[str, Any]]:
    global _LOCAL_ADVISORIES_CACHE
    if _LOCAL_ADVISORIES_CACHE is None:
        if os.path.exists(LOCAL_ADVISORIES_PATH):
            try:
                with open(LOCAL_ADVISORIES_PATH, encoding="utf-8") as f:
                    _LOCAL_ADVISORIES_CACHE = json.load(f)
            except Exception as e:
                print(f"Error loading local_advisories.json: {e}")
                _LOCAL_ADVISORIES_CACHE = []
        else:
            _LOCAL_ADVISORIES_CACHE = []
    return _LOCAL_ADVISORIES_CACHE


def get_gemini_embedding(text: str) -> Optional[list[float]]:
    """Generates a text embedding vector using the Google Gemini REST API."""
    if not GOOGLE_API_KEY:
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={GOOGLE_API_KEY}"
        data = {
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": text}]},
        }
        req_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            return res_body.get("embedding", {}).get("values")
    except Exception as e:
        print(f"Error generating Gemini embedding: {e}")
        return None


async def get_gemini_embedding_async(text: str) -> Optional[list[float]]:
    """Non-blocking async wrapper around get_gemini_embedding."""
    return await asyncio.to_thread(get_gemini_embedding, text)


def query_pest_advisory_local(query_text: str) -> Optional[dict[str, Any]]:
    """Performs a local keyword-matching search against cached advisories."""
    advisories = _load_local_advisories()
    if not advisories:
        return None

    # Normalize user query
    query_lower = query_text.lower()
    query_words = set(query_lower.split())

    best_match = None
    max_score = 0

    for adv in advisories:
        pest = adv.get("pest_or_disease", "").lower()

        # 1. Check direct exact match
        if pest in query_lower:
            return adv

        # 2. Check word overlap score
        pest_words = set(pest.split())
        overlap = len(query_words.intersection(pest_words))

        # Add score if words in the advisory text are matched
        text_words = set(adv.get("advisory_text", "").lower().split())
        text_overlap = len(query_words.intersection(text_words))

        score = (overlap * 5) + text_overlap  # Heavy weight on matching pest name

        if score > max_score and score > 0:
            max_score = score
            best_match = adv

    return best_match


def query_pest_advisory(query_text: str) -> Optional[dict[str, Any]]:
    """Queries verified crop advisories database (synchronous entrypoint)."""
    if SUPABASE_URL and SUPABASE_KEY and GOOGLE_API_KEY:
        try:
            embedding = get_gemini_embedding(query_text)
            if embedding:
                from database import supabase_client

                if supabase_client:
                    rpc_res = supabase_client.rpc(
                        "match_advisories",
                        {
                            "query_embedding": embedding,
                            "match_threshold": 0.7,
                            "match_count": 1,
                        },
                    ).execute()
                    if rpc_res.data:
                        row = rpc_res.data[0]
                        return {
                            "pest_or_disease": row.get("pest_or_disease"),
                            "advisory_text": row.get("advisory_text"),
                            "chemical_recommendation": row.get(
                                "chemical_recommendation"
                            ),
                            "dosage_details": row.get("dosage_details"),
                        }
        except Exception as e:
            print(f"Supabase RAG query failed: {e}. Falling back to local search.")

    return query_pest_advisory_local(query_text)


async def query_pest_advisory_async(query_text: str) -> Optional[dict[str, Any]]:
    """Non-blocking async entrypoint for pest advisory queries."""
    return await asyncio.to_thread(query_pest_advisory, query_text)
