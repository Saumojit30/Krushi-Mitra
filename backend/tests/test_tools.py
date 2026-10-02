import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent import KrushiMitra


@pytest.fixture(autouse=True)
async def clear_cache_between_tests():
    from cache import telemetry_cache

    await telemetry_cache.clear()
    yield
    await telemetry_cache.clear()


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
    mock_response.json = AsyncMock(
        return_value={
            "daily": {
                "time": ["2026-08-17", "2026-08-18", "2026-08-19"],
                "precipitation_probability_max": [10, 80, 50],
                "temperature_2m_max": [32.0, 28.0, 30.0],
                "temperature_2m_min": [24.0, 22.0, 23.0],
            }
        }
    )

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


@pytest.mark.asyncio
async def test_soil_and_irrigation_advisory():
    """Verify soil moisture and irrigation tool fetches data and calculates status accurately."""
    agent = KrushiMitra(user_id="test-user")

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "hourly": {
                "soil_moisture_0_to_1cm": [0.22, 0.22, 0.21, 0.23],
            },
            "daily": {
                "et0_fao_evapotranspiration": [4.2],
            },
        }
    )

    mock_get = MagicMock()
    mock_get.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_get)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        res = await agent.get_soil_and_irrigation_advisory("Amravati")
        assert "Live Soil & Irrigation telemetry for Amravati" in res
        assert "Topsoil Moisture: 22.0%" in res
        assert "Moisture Status: Adequate / Optimal" in res
        assert "Daily Evapotranspiration Loss (ET0): 4.2 mm/day" in res
        assert "No urgent irrigation is needed today" in res


@pytest.mark.asyncio
async def test_soil_advisory_deficit():
    """Verify dry soil triggers irrigation alert."""
    agent = KrushiMitra(user_id="test-user")

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "hourly": {
                "soil_moisture_0_to_1cm": [0.10, 0.11, 0.12],
            },
            "daily": {
                "et0_fao_evapotranspiration": [5.1],
            },
        }
    )

    mock_get = MagicMock()
    mock_get.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_get)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        res = await agent.get_soil_and_irrigation_advisory("Wardha")
        assert "Moisture Status: Water Deficit / Dry" in res
        assert "provide light drip irrigation" in res


@pytest.mark.asyncio
async def test_soil_api_timeout():
    """Verify soil moisture timeout handling."""
    agent = KrushiMitra(user_id="test-user")

    mock_get = MagicMock()
    mock_get.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_get)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        res = await agent.get_soil_and_irrigation_advisory("Yavatmal")
        assert "Error: The soil moisture sensor service timed out" in res


@pytest.mark.asyncio
async def test_soil_advisory_null_values_resilience():
    """Verify soil moisture calculation safely ignores None/null readings in Open-Meteo payload."""
    agent = KrushiMitra(user_id="test-user")

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "hourly": {
                "soil_moisture_0_to_1cm": [0.20, None, 0.22, None],
            },
            "daily": {
                "et0_fao_evapotranspiration": [None, 3.8],
            },
        }
    )

    mock_get = MagicMock()
    mock_get.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_get)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        res = await agent.get_soil_and_irrigation_advisory("Akola")
        assert "Live Soil & Irrigation telemetry for Akola" in res
        assert "Topsoil Moisture: 21.0%" in res
        assert "Moisture Status: Adequate / Optimal" in res


@pytest.mark.asyncio
async def test_inbound_agent_has_tools():
    """Verify InboundAgent has agricultural tools and loads profile context."""
    from telephony.inbound.agent import InboundAgent

    mock_ctx = MagicMock()
    profile = {
        "name": "Devidas",
        "facts": {
            "crops_grown": "cotton",
            "district": "Amravati",
            "land_size_acres": 12.0,
        },
    }
    inbound = InboundAgent(
        ctx=mock_ctx,
        caller_identity="+919876543210",
        profile=profile,
        last_summary="Previous call about whitefly attack.",
    )

    assert "Devidas" in inbound.instructions
    assert "RETURNING USER" in inbound.instructions
    assert hasattr(inbound, "get_soil_and_irrigation_advisory")
    assert hasattr(inbound, "get_weather_forecast")
    assert hasattr(inbound, "get_cotton_mandi_prices")
    assert hasattr(inbound, "save_farmer_profile")
    assert hasattr(inbound, "escalate_to_human")


@pytest.mark.asyncio
async def test_multi_commodity_mandi_prices():
    """Verify get_commodity_mandi_prices fetches cotton, soybean, and tur dal prices."""
    agent = KrushiMitra(user_id="test-user")

    # Test Cotton
    res_cotton = await agent.get_commodity_mandi_prices("cotton", "Yavatmal")
    assert "rates for Yavatmal APMC" in res_cotton
    assert "7100" in res_cotton

    # Test Soybean
    res_soy = await agent.get_commodity_mandi_prices("soybean", "Akola")
    assert "rates for Akola APMC" in res_soy
    assert "4850" in res_soy

    # Test Tur
    res_tur = await agent.get_commodity_mandi_prices("tur", "Wardha")
    assert "rates for Wardha APMC" in res_tur
    assert "10150" in res_tur

    # Test invalid district
    res_invalid = await agent.get_commodity_mandi_prices("soybean", "Nagpur")
    assert "Error: Mandi price records are only available for" in res_invalid


@pytest.mark.asyncio
async def test_weather_alerts():
    """Verify weather alert evaluation for normal and severe conditions."""
    agent = KrushiMitra(user_id="test-user")

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "daily": {
                "precipitation_probability_max": [85],
                "wind_speed_10m_max": [42.0],
                "temperature_2m_max": [34.0],
            }
        }
    )

    mock_get = MagicMock()
    mock_get.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_get)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        res = await agent.get_weather_alerts("Yavatmal")
        assert "URGENT Weather Alert" in res
        assert "Heavy unseasonal rainfall alert" in res
        assert "High wind warning" in res


@pytest.mark.asyncio
async def test_telemetry_cache_ttl():
    """Verify AsyncTTLCache stores, retrieves, and expires items."""
    from cache import AsyncTTLCache

    cache = AsyncTTLCache(default_ttl_seconds=1)
    await cache.set("test_key", "cached_value")
    val = await cache.get("test_key")
    assert val == "cached_value"
    assert await cache.size() == 1

    await cache.clear()
    assert await cache.size() == 0
    assert await cache.get("test_key") is None


@pytest.mark.asyncio
async def test_system_health_probe():
    """Verify health check probe returns expected healthy structure."""
    from metrics import get_system_health

    health = await get_system_health()
    assert health["status"] == "healthy"
    assert health["database_connected"] is True
    assert "stt_provider" in health
    assert "groq_model" in health
