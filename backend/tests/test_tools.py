import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import aiohttp
from agent import KrushiMitra

@pytest.mark.asyncio
async def test_mandi_price_lookup():
    """Verify cotton mandi price lookup fetches correct prices and handles errors."""
    agent = KrushiMitra(user_id="test-user")
    
    # Test valid district Yavatmal
    res = await agent.get_cotton_mandi_prices("Yavatmal")
    assert "Cotton rates for Yavatmal APMC" in res
    assert "Average modal price: 7100" in res
    assert "MSP: 6620" in res
    
    # Test valid district Wardha (case insensitive)
    res = await agent.get_cotton_mandi_prices("wardha")
    assert "Wardha APMC" in res
    assert "Average modal price: 7000" in res
    
    # Test invalid district
    res = await agent.get_cotton_mandi_prices("Nagpur")
    assert "Error" in res
    assert "Cotton price records are only available for" in res

@pytest.mark.asyncio
async def test_weather_coordinates_mapping():
    """Verify weather tool maps target districts correctly and defaults to Yavatmal."""
    agent = KrushiMitra(user_id="test-user")
    
    # Mock ClientSession and its get method
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "daily": {
            "time": ["2026-08-17", "2026-08-18", "2026-08-19"],
            "precipitation_probability_max": [10, 80, 50],
            "temperature_2m_max": [32.0, 28.0, 30.0],
            "temperature_2m_min": [24.0, 22.0, 23.0]
        }
    })
    
    mock_get = MagicMock()
    mock_get.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get.__aexit__ = AsyncMock(return_value=None)
    
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_get)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        # Test valid district Akola
        res = await agent.get_weather_forecast("Akola")
        assert "Live 3-day weather forecast for Akola" in res
        assert "Rain Probability: 80%" in res
        assert "Temp: 22.0 to 28.0" in res
        
        # Test unrecognized district falls back to Yavatmal
        res = await agent.get_weather_forecast("Pune")
        assert "Live 3-day weather forecast for Yavatmal (default)" in res

@pytest.mark.asyncio
async def test_weather_api_timeout():
    """Verify weather tool handles timeout errors out loud."""
    agent = KrushiMitra(user_id="test-user")
    
    # Mock ClientSession to raise TimeoutError
    mock_get = MagicMock()
    mock_get.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
    
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_get)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        res = await agent.get_weather_forecast("Yavatmal")
        assert "Error: The live weather service timed out" in res
        assert "recommend checking rain signs manually" in res
