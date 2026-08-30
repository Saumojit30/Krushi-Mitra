import pytest

from agent import CottonPestSpecialist
from rag_utility import query_pest_advisory


def test_rag_utility_local_fallback():
    """Verify that the RAG utility matches queries using local keyword fallback correctly."""
    # Test pink bollworm match
    res = query_pest_advisory("माझ्या कापसावर बोंड अळी (pink bollworm) आहे")
    assert res is not None
    assert res["pest_or_disease"] == "pink bollworm"
    assert "Emamectin" in res["chemical_recommendation"]

    # Test sucking pests match
    res2 = query_pest_advisory("Aphids चा प्रादुर्भाव आहे")
    assert res2 is not None
    assert res2["pest_or_disease"] == "aphids"
    assert "Thiamethoxam" in res2["chemical_recommendation"]

    # Test non-matching query
    res3 = query_pest_advisory("How to grow apples in Nagpur?")
    assert res3 is None


@pytest.mark.asyncio
async def test_specialist_rag_tool():
    """Verify that the CottonPestSpecialist get_verified_pest_remedy tool retrieves and returns the advisory."""
    pest = CottonPestSpecialist(user_id="test-farmer")

    # Check valid pest match
    result = await pest.get_verified_pest_remedy("pink bollworm")
    assert "Verified Advisory for pink bollworm" in result
    assert "Emamectin" in result
    assert "4 grams per 10 liters" in result

    # Check invalid pest match
    result_invalid = await pest.get_verified_pest_remedy("apple infestation")
    assert "No verified government remedy found" in result_invalid
