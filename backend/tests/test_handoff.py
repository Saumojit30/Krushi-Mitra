from unittest.mock import AsyncMock, MagicMock

import pytest

from agent import CottonMarketSpecialist, CottonPestSpecialist, KrushiMitra


def test_specialist_instantiation():
    """Verify that all specialized agents are correctly instantiated with their custom prompts."""
    pest = CottonPestSpecialist(user_id="test-farmer", profile={"name": "Sanjay"})
    assert pest.user_id == "test-farmer"
    assert pest.profile["name"] == "Sanjay"
    assert "कापूस कीड व रोग नियंत्रण तज्ज्ञ" in pest.instructions

    market = CottonMarketSpecialist(user_id="test-farmer", profile={"name": "Sanjay"})
    assert market.user_id == "test-farmer"
    assert market.profile["name"] == "Sanjay"
    assert "कापूस बाजार व सीसीआय खरेदी तज्ज्ञ" in market.instructions


@pytest.mark.asyncio
async def test_handoff_triage_to_pest():
    """Verify that triage agent hands off to pest specialist and copies chat history."""
    triage = KrushiMitra(user_id="test-farmer", profile={"name": "Namdev"})

    ctx = triage.chat_ctx.copy()
    ctx.add_message(role="user", content="कापसावर बोंड अळी पडली आहे.")
    await triage.update_chat_ctx(ctx)

    # Mock the LiveKit session and context
    mock_session = MagicMock()
    mock_session.update_agent = MagicMock()
    mock_session.say = AsyncMock()

    triage._lk_session = mock_session
    triage._lk_ctx = MagicMock()

    # Run handoff tool
    result = await triage.handoff_to_pest_specialist()

    assert "Transferred successfully" in result
    # Check that update_agent was called with CottonPestSpecialist
    mock_session.update_agent.assert_called_once()
    called_agent = mock_session.update_agent.call_args[0][0]
    assert isinstance(called_agent, CottonPestSpecialist)

    # Check context copy
    assert len(called_agent.chat_ctx.messages()) == 1
    assert called_agent.chat_ctx.messages()[0].content[0] == "कापसावर बोंड अळी पडली आहे."

    # Check transition announcement speech
    mock_session.say.assert_called_once()
    assert (
        "कापूस कीड आणि रोग नियंत्रण तज्ज्ञांकडे हस्तांतरित करत आहे"
        in mock_session.say.call_args[0][0]
    )


@pytest.mark.asyncio
async def test_handoff_pest_to_market():
    """Verify that pest specialist hands off to market specialist and transfers chat history."""
    pest = CottonPestSpecialist(user_id="test-farmer", profile={"name": "Namdev"})

    ctx = pest.chat_ctx.copy()
    ctx.add_message(role="user", content="कापसाचा आजचा हमीभाव काय आहे?")
    await pest.update_chat_ctx(ctx)

    # Mock session
    mock_session = MagicMock()
    mock_session.update_agent = MagicMock()
    mock_session.say = AsyncMock()
    pest._lk_session = mock_session
    pest._lk_ctx = MagicMock()

    # Run handoff tool
    result = await pest.handoff_to_market_specialist()

    assert "Transferred successfully" in result
    mock_session.update_agent.assert_called_once()
    called_agent = mock_session.update_agent.call_args[0][0]
    assert isinstance(called_agent, CottonMarketSpecialist)

    # Check context copy
    assert len(called_agent.chat_ctx.messages()) == 1
    assert (
        called_agent.chat_ctx.messages()[0].content[0] == "कापसाचा आजचा हमीभाव काय आहे?"
    )

    # Check transition announcement speech
    mock_session.say.assert_called_once()
    assert (
        "कापूस बाजार आणि हमीभाव तज्ज्ञांकडे हस्तांतरित करत आहे"
        in mock_session.say.call_args[0][0]
    )


@pytest.mark.asyncio
async def test_handoff_market_to_triage():
    """Verify that market specialist hands off back to triage and transfers chat history."""
    market = CottonMarketSpecialist(user_id="test-farmer", profile={"name": "Namdev"})

    ctx = market.chat_ctx.copy()
    ctx.add_message(role="user", content="हवामान काय आहे?")
    await market.update_chat_ctx(ctx)

    # Mock session
    mock_session = MagicMock()
    mock_session.update_agent = MagicMock()
    mock_session.say = AsyncMock()
    market._lk_session = mock_session
    market._lk_ctx = MagicMock()

    # Run handoff tool
    result = await market.handoff_to_triage()

    assert "Transferred successfully" in result
    mock_session.update_agent.assert_called_once()
    called_agent = mock_session.update_agent.call_args[0][0]
    assert isinstance(called_agent, KrushiMitra)

    # Check context copy
    assert len(called_agent.chat_ctx.messages()) == 1
    assert called_agent.chat_ctx.messages()[0].content[0] == "हवामान काय आहे?"

    # Check transition announcement speech
    mock_session.say.assert_called_once()
    assert "मुख्य सहाय्यकाकडे परत हस्तांतरित करत आहे" in mock_session.say.call_args[0][0]
