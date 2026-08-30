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


def query_pest_advisory_local(query_text: str) -> Optional[dict[str, Any]]:
    """Performs a local keyword-matching search against local_advisories.json."""
    if not os.path.exists(LOCAL_ADVISORIES_PATH):
        return None

    try:
        with open(LOCAL_ADVISORIES_PATH, encoding="utf-8") as f:
            advisories = json.load(f)
    except Exception as e:
        print(f"Error loading local_advisories.json: {e}")
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
            # High priority direct match
            return adv

        # 2. Check word overlap score
        pest_words = set(pest.split())
        overlap = len(query_words.intersection(pest_words))

        # Add score if words in the advisory text are matched
        text_words = set(adv.get("advisory_text", "").lower().split())
        text_overlap = len(query_words.intersection(text_words))

        score = (overlap * 5) + text_overlap  # Heavy weight on matching the pest name

        if score > max_score and score > 0:
            max_score = score
            best_match = adv

    return best_match


def query_pest_advisory(query_text: str) -> Optional[dict[str, Any]]:
    """Queries the verified crop advisories database.
    Performs vector similarity search if Supabase and Gemini are set up;
    otherwise falls back to local keyword search.
    """
    if SUPABASE_URL and SUPABASE_KEY and GOOGLE_API_KEY:
        try:
            # 1. Generate Query Embedding
            embedding = get_gemini_embedding(query_text)
            if embedding:
                # 2. Query Supabase using cosine similarity RPC
                # We expect a Supabase RPC function named 'match_advisories' to be defined
                # or we can query the table directly if needed.
                # However, raw select cannot do vector distance unless using RPC or custom raw SQL.
                # Let's call the 'match_advisories' RPC function
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

    # Fallback to local search
    return query_pest_advisory_local(query_text)
