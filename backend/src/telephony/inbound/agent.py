"""Inbound telephony agent — answers incoming phone calls.

A caller dials your phone number, your SIP provider forwards the call to LiveKit,
and LiveKit's dispatch rule routes it to this agent by name ("inbound-agent").

Run it with:

    uv run python src/telephony/inbound/agent.py dev

See src/telephony/README.md for the trunk and dispatch rule setup.
"""

import json
import logging
import os

from dotenv import load_dotenv
from livekit import api, rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.plugins import murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from prompts import (
    MARKET_SPECIALIST_PROMPT,
    PEST_SPECIALIST_PROMPT,
    SYSTEM_PROMPT,
)
from rag_utility import query_pest_advisory_async

logger = logging.getLogger("inbound-agent")

load_dotenv(".env.local")

# Optional — a phone number to transfer callers to when they ask for a human.
TRANSFER_TO_NUMBER = os.getenv("TRANSFER_TO_NUMBER")

MURF_VOICE_ID = os.getenv("MURF_VOICE_ID", "mr-IN-shilpa")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GREETING = "Namaskar! Mee Krushi Mitra — Vidarbhyatil kapas shetkaryasathi. Aaj tumhala kaay madat karaychi ahe?"

# In-memory cache for static mandi prices dataset
_MANDI_PRICES_CACHE: dict | None = None


def _get_mandi_prices_data() -> dict:
    global _MANDI_PRICES_CACHE
    if _MANDI_PRICES_CACHE is None:
        mandi_file = os.path.join(
            os.path.dirname(__file__), "..", "..", "mandi_prices.json"
        )
        if os.path.exists(mandi_file):
            try:
                with open(mandi_file, encoding="utf-8") as f:
                    _MANDI_PRICES_CACHE = json.load(f)
            except Exception as e:
                logger.error("Failed to load mandi_prices.json: %s", e)
                _MANDI_PRICES_CACHE = {}
        else:
            _MANDI_PRICES_CACHE = {}
    return _MANDI_PRICES_CACHE


class InboundAgent(Agent):
    def __init__(
        self,
        ctx: JobContext,
        caller_identity: str | None,
        profile: dict | None = None,
        last_summary: str | None = None,
        start_time: float | None = None,
    ) -> None:
        self.ctx = ctx
        self.caller_identity = caller_identity
        self.user_id = caller_identity or "anonymous-phone"
        self.profile = profile or {}
        self.last_summary = last_summary
        self.start_time = start_time
        self._lk_session = None
        self._lk_ctx = ctx
        self.tool_executed = False
        self.error_log = None

        instructions = SYSTEM_PROMPT

        profile_context = []
        if self.profile.get("name"):
            profile_context.append(f"Name: {self.profile['name']}")

        facts = self.profile.get("facts", {})
        if facts.get("crops_grown"):
            profile_context.append(f"Crops grown: {facts['crops_grown']}")
        if facts.get("land_size_acres"):
            profile_context.append(f"Land size: {facts['land_size_acres']} acres")
        if facts.get("district"):
            profile_context.append(f"District: {facts['district']}")
        if facts.get("irrigation_type"):
            profile_context.append(f"Irrigation type: {facts['irrigation_type']}")

        if profile_context:
            context_str = "\n".join(profile_context)
            instructions = f"[FARMER PROFILE]\n{context_str}\n\n{instructions}"

        if self.last_summary:
            instructions = f"[LAST CALL SUMMARY]\n{self.last_summary}\n\n{instructions}"

        if self.profile.get("name"):
            name = self.profile["name"]
            returning_instruction = (
                f"[RETURNING USER]\n"
                f"You are talking to a returning user named {name}. "
                f'Greet them warmly by name in Marathi: "Namaskar {name} bhau, Krushi Mitra var tumche punha swagat ahe!" '
                f"If a last call summary is present under [LAST CALL SUMMARY], follow up or reference it.\n\n"
            )
            instructions = returning_instruction + instructions

        super().__init__(instructions=instructions)

    @function_tool
    async def transfer_to_human(self, context: RunContext) -> str:
        """Transfer the caller to a human colleague.

        Use this when the caller explicitly asks for a person, or when you cannot
        help them with their request.
        """
        if not TRANSFER_TO_NUMBER or not self.caller_identity:
            return "Transfers are not available on this line. Offer to take a message instead."

        # Tell the caller before transferring — the SIP transfer cuts off the audio.
        await context.session.generate_reply(
            instructions="Tell the caller you're connecting them to a colleague now."
        )

        logger.info("transferring caller to %s", TRANSFER_TO_NUMBER)
        try:
            await self.ctx.api.sip.transfer_sip_participant(
                api.TransferSIPParticipantRequest(
                    room_name=self.ctx.room.name,
                    participant_identity=self.caller_identity,
                    transfer_to=f"tel:{TRANSFER_TO_NUMBER}",
                    play_dialtone=True,
                )
            )
        except Exception:
            logger.exception("transfer failed")
            return "The transfer did not go through. Apologize and offer to take a message."

        return "Transferred."

    @function_tool
    async def end_call(self, context: RunContext) -> str:
        """Hang up the call.

        Use this only once the caller has said goodbye or the conversation is clearly over.
        """
        # Let the agent finish its closing line before the call drops.
        await context.session.generate_reply(
            instructions="Say a short, warm goodbye to the caller."
        )

        logger.info("ending call")
        await self.ctx.api.room.delete_room(
            api.DeleteRoomRequest(room=self.ctx.room.name)
        )
        return "Call ended."

    @function_tool
    async def save_farmer_profile(
        self,
        name: str,
        district: str,
        land_size_acres: float,
        crops_grown: str,
        irrigation_type: str,
        consent_given: bool = False,
    ) -> str:
        """Save or update the farmer's profile in the database.

        Parameters:
        - name: The farmer's full name.
        - district: The district in Vidarbha (Yavatmal, Amravati, Akola, Wardha).
        - land_size_acres: Size of their farm in acres (e.g., 5.0).
        - crops_grown: Primary crops (e.g., 'cotton', 'soybean').
        - irrigation_type: 'rainfed' (koradvahu) or 'irrigated' (bagayati).
        - consent_given: True if the farmer explicitly gave verbal consent.
        """
        if not consent_given:
            return "Consent not given. Do not save profile data."

        facts = {
            "crops_grown": crops_grown,
            "district": district,
            "land_size_acres": land_size_acres,
            "irrigation_type": irrigation_type,
        }

        try:
            from database import async_save_farmer

            await async_save_farmer(
                user_id=self.user_id,
                name=name,
                language_preference="mr",
                facts=facts,
            )
            self.profile = {"name": name, "facts": facts}
            self.tool_executed = True
            logger.info("Saved farmer profile for user: %s", self.user_id)
            return f"Profile successfully saved for {name}."
        except Exception as e:
            logger.error("Failed to save farmer profile: %s", e)
            self.error_log = f"Failed to save profile: {e}"
            return "Failed to save profile."

    @function_tool
    async def escalate_to_human(
        self,
        farmer_name: str,
        issue_summary: str,
        crop_stage: str,
        urgency: str,
        verbal_consent_given: bool = False,
    ) -> str:
        """Submit a formal ticket to connect the farmer with a human agricultural officer (KVK Specialist).

        Parameters:
        - farmer_name: Name of the farmer.
        - issue_summary: Factual summary of the issue.
        - crop_stage: Current stage of the cotton crop.
        - urgency: 'HIGH' or 'MEDIUM'.
        - verbal_consent_given: True ONLY if farmer explicitly agreed.
        """
        if not verbal_consent_given:
            return (
                "Consent not granted. Do not escalate to agricultural officer. "
                "Inform the farmer you respect their decision and continue regular advice."
            )

        try:
            from database import async_create_escalation

            full_summary = (
                f"Farmer: {farmer_name} | Stage: {crop_stage} | Issue: {issue_summary}"
            )
            ticket_id = await async_create_escalation(
                user_id=self.user_id,
                reason="Severe crop damage / specialist request",
                summary=full_summary,
                urgency=urgency,
            )
            self.tool_executed = True
            logger.info("Escalation created #%s for user %s", ticket_id, self.user_id)
            return (
                f"Escalation ticket #{ticket_id} created with {urgency} priority. "
                f"Inform the farmer in Marathi that their complaint is submitted to the KVK officer."
            )
        except Exception as e:
            logger.error("Failed to create escalation ticket: %s", e)
            self.error_log = f"Escalation failed: {e}"
            return "Failed to submit escalation ticket."

    @function_tool
    async def get_weather_forecast(self, district: str) -> str:
        """Fetch the live 3-day weather forecast for a specific district in Vidarbha (Yavatmal, Amravati, Akola, Wardha).

        Parameters:
        - district: The district name (e.g., 'Yavatmal', 'Amravati', 'Akola', 'Wardha').
        """
        import asyncio

        import aiohttp

        coords = {
            "yavatmal": (20.389, 78.131),
            "amravati": (20.932, 77.752),
            "akola": (20.700, 77.008),
            "wardha": (20.745, 78.602),
        }

        cleaned_district = district.strip().lower()
        if cleaned_district not in coords:
            logger.warning(
                "Unrecognized district requested: %s. Defaulting to Yavatmal.",
                district,
            )
            lat, lon = coords["yavatmal"]
            target_name = "Yavatmal (default)"
        else:
            lat, lon = coords[cleaned_district]
            target_name = district.strip().capitalize()

        from cache import telemetry_cache

        cache_key = (
            f"weather_{cleaned_district if cleaned_district in coords else 'yavatmal'}"
        )
        cached = await telemetry_cache.get(cache_key)
        if cached:
            self.tool_executed = True
            return cached

        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            f"&timezone=Asia%2FKolkata&forecast_days=3"
        )

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(url, timeout=aiohttp.ClientTimeout(total=5.0)) as response,
            ):
                if response.status != 200:
                    return f"Error: Could not retrieve weather data. API responded with status {response.status}."

                data = await response.json()
                daily = data.get("daily", {})
                if not daily or "time" not in daily:
                    return "Error: Weather data formatting was unrecognized."

                forecasts = []
                for i in range(len(daily["time"])):
                    date = daily["time"][i]
                    rain_prob = daily["precipitation_probability_max"][i]
                    temp_max = daily["temperature_2m_max"][i]
                    temp_min = daily["temperature_2m_min"][i]
                    forecasts.append(
                        f"Date: {date}, Rain Probability: {rain_prob}%, "
                        f"Temp: {temp_min} to {temp_max} degrees Celsius"
                    )

                forecast_str = "\n".join(forecasts)
                self.tool_executed = True
                result_msg = f"Live 3-day weather forecast for {target_name} (retrieved today):\n{forecast_str}"
                await telemetry_cache.set(cache_key, result_msg)
                return result_msg

        except asyncio.TimeoutError:
            logger.error("Weather API call timed out.")
            self.error_log = "Weather API call timed out"
            return "Error: The live weather service timed out. Please tell the farmer that the weather system is temporarily busy, and recommend checking rain signs manually."
        except Exception as e:
            logger.error("Weather API failed with exception: %s", e)
            self.error_log = f"Weather API failed with exception: {e}"
            return "Error: Failed to connect to the weather service due to a technical error."

    @function_tool
    async def get_soil_and_irrigation_advisory(self, district: str) -> str:
        """Fetch live soil moisture (0-3cm) and daily evapotranspiration (ET0) for a specific district
        in Vidarbha (Yavatmal, Amravati, Akola, Wardha) to provide scientific irrigation advice for cotton crops.

        Parameters:
        - district: The district name (e.g., 'Yavatmal', 'Amravati', 'Akola', 'Wardha').
        """
        import asyncio

        import aiohttp

        coords = {
            "yavatmal": (20.389, 78.131),
            "amravati": (20.932, 77.752),
            "akola": (20.700, 77.008),
            "wardha": (20.745, 78.602),
        }

        cleaned_district = district.strip().lower()
        if cleaned_district not in coords:
            logger.warning(
                "Unrecognized district requested for soil data: %s. Defaulting to Yavatmal.",
                district,
            )
            lat, lon = coords["yavatmal"]
            target_name = "Yavatmal (default)"
        else:
            lat, lon = coords[cleaned_district]
            target_name = district.strip().capitalize()

        from cache import telemetry_cache

        cache_key = (
            f"soil_{cleaned_district if cleaned_district in coords else 'yavatmal'}"
        )
        cached = await telemetry_cache.get(cache_key)
        if cached:
            self.tool_executed = True
            return cached

        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&hourly=soil_moisture_0_to_1cm"
            f"&daily=et0_fao_evapotranspiration"
            f"&timezone=Asia%2FKolkata&forecast_days=1"
        )

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(url, timeout=aiohttp.ClientTimeout(total=5.0)) as response,
            ):
                if response.status != 200:
                    return f"Error: Could not retrieve soil data. API responded with status {response.status}."

                data = await response.json()
                hourly = data.get("hourly", {})
                daily = data.get("daily", {})

                moisture_readings = hourly.get("soil_moisture_0_to_1cm", [])
                et0_readings = daily.get("et0_fao_evapotranspiration", [])

                valid_moisture = [
                    m for m in moisture_readings if isinstance(m, (int, float))
                ]
                if not valid_moisture:
                    return "Error: Soil moisture data was unavailable."

                avg_moisture = sum(valid_moisture) / len(valid_moisture)
                moisture_pct = round(avg_moisture * 100, 1)
                valid_et0 = [e for e in et0_readings if isinstance(e, (int, float))]
                et0_val = valid_et0[0] if valid_et0 else 3.5

                if moisture_pct < 15.0:
                    status = "Water Deficit / Dry"
                    advice = (
                        "Soil moisture is critically low. If your cotton crop is in flowering or boll development stage, "
                        "provide light drip irrigation in the morning or evening to prevent flower and boll drop."
                    )
                elif moisture_pct <= 32.0:
                    status = "Adequate / Optimal"
                    advice = (
                        "Soil root zone has sufficient moisture. No urgent irrigation is needed today. "
                        "Rainfed crops are healthy."
                    )
                else:
                    status = "High Moisture / Saturated"
                    advice = (
                        "Soil has excessive moisture. Ensure drainage channels are clear to prevent waterlogging, "
                        "root rot, or fungal wilt."
                    )

                self.tool_executed = True
                result_msg = (
                    f"Live Soil & Irrigation telemetry for {target_name}:\n"
                    f"- Topsoil Moisture: {moisture_pct}% (m3/m3 equivalent: {round(avg_moisture, 3)})\n"
                    f"- Moisture Status: {status}\n"
                    f"- Daily Evapotranspiration Loss (ET0): {et0_val} mm/day\n"
                    f"- Agronomic Advice: {advice}"
                )
                await telemetry_cache.set(cache_key, result_msg)
                return result_msg

        except asyncio.TimeoutError:
            logger.error("Soil moisture API call timed out.")
            self.error_log = "Soil API timed out"
            return "Error: The soil moisture sensor service timed out. Recommend manually checking root zone moisture by digging 2 inches."
        except Exception as e:
            logger.error("Soil API failed: %s", e)
            self.error_log = f"Soil API failed: {e}"
            return "Error: Failed to fetch live soil data due to a network error."

    @function_tool
    async def get_cotton_mandi_prices(self, district: str) -> str:
        """Fetch the cotton mandi (APMC) market prices for a specific district in Vidarbha (Yavatmal, Amravati, Akola, Wardha)."""
        cleaned_district = district.strip().lower()
        target_district = None
        for key in ["Yavatmal", "Amravati", "Akola", "Wardha"]:
            if key.lower() == cleaned_district:
                target_district = key
                break

        if not target_district:
            return (
                "Error: Cotton price records are only available for Yavatmal, Amravati, Akola, and Wardha. "
                "Please tell the farmer you only have prices for these locations."
            )

        try:
            data = _get_mandi_prices_data()
            prices_dict = data.get("prices", {})
            district_prices = prices_dict.get(target_district)

            if not district_prices:
                return f"Error: No price details found for {target_district}."

            mandi_name = district_prices["mandi_name"]
            min_price = district_prices["min_price"]
            max_price = district_prices["max_price"]
            modal_price = district_prices["modal_price"]
            msp_ref = district_prices["msp_reference"]

            self.tool_executed = True
            return (
                f"Cotton rates for {mandi_name} from yesterday's close (August 16, 2026):\n"
                f"- Minimum price: {min_price} rupees per quintal\n"
                f"- Maximum price: {max_price} rupees per quintal\n"
                f"- Average modal price: {modal_price} rupees per quintal\n"
                f"- Reference Government MSP: {msp_ref} rupees per quintal."
            )
        except Exception as e:
            logger.error("Failed to load cotton mandi prices: %s", e)
            self.error_log = f"Failed to load cotton mandi prices: {e}"
            return (
                "Error: Could not retrieve market prices due to a local server error."
            )

    async def on_session_end(self) -> None:
        """Save call summary to SQLite when inbound call ends."""
        import time

        duration = 0
        if self.start_time:
            duration = int(time.time() - self.start_time)

        outcome = "FAILURE"
        error_msg = None

        if self.error_log:
            outcome = "FAILURE"
            error_msg = self.error_log
        elif self.tool_executed and duration >= 10:
            outcome = "SUCCESS"
        else:
            outcome = "FAILURE"
            if duration < 10:
                error_msg = "Call ended too early (short duration)"
            else:
                error_msg = "No advisory action / tool executed during the call"

        if self._lk_session and self._lk_ctx:
            messages = list(self._lk_session.history.messages)
            has_dialogue = any(m.role in ("user", "assistant") for m in messages)
            if has_dialogue:
                try:
                    dialogue = []
                    for m in messages:
                        if m.role in ("user", "assistant"):
                            content = m.content
                            if isinstance(content, list):
                                content = " ".join(str(c) for c in content)
                            dialogue.append(f"{m.role.upper()}: {content}")

                    dialogue_text = "\n".join(dialogue)
                    llm = self._lk_session.llm
                    from livekit.agents.llm.chat_context import ChatContext

                    summary_prompt = (
                        "You are Krushi Mitra's internal summarizer. "
                        "Summarize this inbound farmer query call in Marathi. "
                        "Make it 1 to 2 sentences. Focus on what was asked and what advisory was provided. "
                        "Do not include greeting or conversational filler. Keep it strictly factual.\n\n"
                        f"Conversation:\n{dialogue_text}"
                    )

                    ctx = ChatContext()
                    ctx.add_message(role="user", content=summary_prompt)

                    response = await llm.chat(chat_ctx=ctx).collect()
                    summary_text = response.text.strip()

                    if summary_text:
                        from database import async_save_call_summary

                        await async_save_call_summary(
                            self.user_id,
                            summary_text,
                            duration_seconds=duration,
                            outcome=outcome,
                            error_log=error_msg,
                            call_type="INBOUND",
                        )
                        logger.info(
                            "Saved inbound call summary for %s: %s",
                            self.user_id,
                            summary_text,
                        )
                except Exception as e:
                    logger.error(
                        "Failed to generate and save inbound call summary: %s", e
                    )

    @function_tool
    async def get_commodity_mandi_prices(self, commodity: str, district: str) -> str:
        """Fetch mandi (APMC) market prices for agricultural crops: cotton (कापूस), soybean (सोयाबीन), or tur (तूर डाळ)
        in a specific district of Vidarbha (Yavatmal, Amravati, Akola, Wardha).

        Parameters:
        - commodity: Crop name such as 'cotton', 'soybean', or 'tur'.
        - district: The district name (e.g., 'Yavatmal', 'Amravati', 'Akola', 'Wardha').
        """
        cleaned_district = district.strip().lower()
        target_district = None
        for key in ["Yavatmal", "Amravati", "Akola", "Wardha"]:
            if key.lower() == cleaned_district:
                target_district = key
                break

        if not target_district:
            return (
                "Error: Mandi price records are only available for Yavatmal, Amravati, Akola, and Wardha. "
                "Please tell the farmer you only have prices for these locations."
            )

        cleaned_comm = commodity.strip().lower()
        comm_key = "cotton"
        if "soy" in cleaned_comm or "सोयाबीन" in cleaned_comm:
            comm_key = "soybean"
        elif "tur" in cleaned_comm or "तूर" in cleaned_comm or "arhar" in cleaned_comm:
            comm_key = "tur"
        elif (
            "cotton" in cleaned_comm
            or "कापूस" in cleaned_comm
            or "kapas" in cleaned_comm
        ):
            comm_key = "cotton"

        try:
            data = _get_mandi_prices_data()
            comm_dict = data.get("commodities", {}).get(comm_key, {})
            districts_dict = comm_dict.get("districts", {})
            district_prices = districts_dict.get(target_district)

            if not district_prices and comm_key == "cotton":
                district_prices = data.get("prices", {}).get(target_district)

            if not district_prices:
                return (
                    f"Error: No {comm_key} price details found for {target_district}."
                )

            mandi_name = district_prices.get("mandi_name", f"{target_district} APMC")
            min_price = district_prices["min_price"]
            max_price = district_prices["max_price"]
            modal_price = district_prices["modal_price"]
            msp_ref = comm_dict.get("msp", district_prices.get("msp_reference", 6620))
            name_mr = comm_dict.get("name_mr", comm_key)

            self.tool_executed = True
            return (
                f"{name_mr.capitalize()} rates for {mandi_name} from yesterday's close:\n"
                f"- Minimum price: {min_price} rupees per quintal\n"
                f"- Maximum price: {max_price} rupees per quintal\n"
                f"- Average modal price: {modal_price} rupees per quintal\n"
                f"- Reference Government MSP: {msp_ref} rupees per quintal."
            )
        except Exception as e:
            logger.error("Failed to load commodity mandi prices: %s", e)
            self.error_log = f"Failed to load commodity mandi prices: {e}"
            return (
                "Error: Could not retrieve market prices due to a local server error."
            )

    @function_tool
    async def get_weather_alerts(self, district: str) -> str:
        """Check for severe weather alerts (unseasonal rain, thunderstorms, high winds, heatwaves) for a district in Vidarbha.

        Parameters:
        - district: The district name (e.g., 'Yavatmal', 'Amravati', 'Akola', 'Wardha').
        """
        import asyncio

        import aiohttp

        from cache import telemetry_cache

        coords = {
            "yavatmal": (20.389, 78.131),
            "amravati": (20.932, 77.752),
            "akola": (20.700, 77.008),
            "wardha": (20.745, 78.602),
        }

        cleaned_district = district.strip().lower()
        if cleaned_district not in coords:
            lat, lon = coords["yavatmal"]
            target_name = "Yavatmal (default)"
            cache_key = "alert_yavatmal"
        else:
            lat, lon = coords[cleaned_district]
            target_name = district.strip().capitalize()
            cache_key = f"alert_{cleaned_district}"

        cached = await telemetry_cache.get(cache_key)
        if cached:
            self.tool_executed = True
            return cached

        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&daily=precipitation_probability_max,wind_speed_10m_max,temperature_2m_max"
            f"&timezone=Asia%2FKolkata&forecast_days=1"
        )

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(url, timeout=aiohttp.ClientTimeout(total=5.0)) as response,
            ):
                if response.status != 200:
                    return f"Error: Could not retrieve weather alert data (status {response.status})."

                data = await response.json()
                daily = data.get("daily", {})
                rain_prob = daily.get("precipitation_probability_max", [0])[0] or 0
                max_wind = daily.get("wind_speed_10m_max", [0])[0] or 0
                max_temp = daily.get("temperature_2m_max", [30])[0] or 30

                alerts = []
                if rain_prob >= 70:
                    alerts.append(
                        f"Heavy unseasonal rainfall alert ({rain_prob}% probability). Secure picked cotton in dry storage immediately."
                    )
                if max_wind >= 35:
                    alerts.append(
                        f"High wind warning ({max_wind} km/h). Delay foliar pesticide spraying to prevent drift."
                    )
                if max_temp >= 42:
                    alerts.append(
                        f"Severe heatwave advisory ({max_temp}°C). Irrigate early morning to prevent boll shedding."
                    )

                if not alerts:
                    res = f"Weather Alert Status for {target_name}: No severe weather warnings active today. Normal agricultural operations safe."
                else:
                    res = f"URGENT Weather Alert for {target_name}:\n" + "\n".join(
                        f"- {a}" for a in alerts
                    )

                await telemetry_cache.set(cache_key, res)
                self.tool_executed = True
                return res
        except asyncio.TimeoutError:
            return "Error: Weather alert service timed out. Please proceed with standard precautions."
        except Exception as e:
            return f"Error: Unable to fetch weather alerts due to technical error: {e}"

    @function_tool
    async def handoff_to_pest_specialist(self) -> str:
        """Call this tool immediately when the farmer asks questions about crop pests,
        insect infestation, pink bollworm, crop diseases, plant damage, or pesticide spraying.
        This hands the call over to the specialized Cotton Pest & Disease Specialist.
        """
        logger.info("Triage handing over to Cotton Pest Specialist...")
        pest = CottonPestSpecialist(
            ctx=self.ctx,
            caller_identity=self.caller_identity,
            start_time=self.start_time,
        )
        pest._lk_session = self._lk_session
        pest._lk_ctx = self._lk_ctx
        pest.tool_executed = True

        # Copy context messages
        ctx = pest.chat_ctx.copy()
        for msg in self.chat_ctx.messages():
            ctx.add_message(role=msg.role, content=msg.content)
        await pest.update_chat_ctx(ctx)

        if self._lk_session:
            self._lk_session.update_agent(pest)
            await self._lk_session.say(
                "मी आपल्याला आमच्या कापूस कीड आणि रोग नियंत्रण तज्ज्ञांकडे हस्तांतरित करत आहे. कृपया एक सेकंद थांबा.",
                allow_interruptions=True,
            )

        return "Transferred successfully to the Cotton Pest & Disease Specialist."

    @function_tool
    async def handoff_to_market_specialist(self) -> str:
        """Call this tool immediately when the farmer asks questions about Cotton Corporation of India (CCI)
        buying centers, government MSP purchase process, moisture grading, or necessary land/bank papers.
        This hands the call over to the specialized Cotton Market & CCI Procurement Specialist.
        """
        logger.info("Triage handing over to Cotton Market Specialist...")
        market = CottonMarketSpecialist(
            ctx=self.ctx,
            caller_identity=self.caller_identity,
            start_time=self.start_time,
        )
        market._lk_session = self._lk_session
        market._lk_ctx = self._lk_ctx
        market.tool_executed = True

        # Copy context messages
        ctx = market.chat_ctx.copy()
        for msg in self.chat_ctx.messages():
            ctx.add_message(role=msg.role, content=msg.content)
        await market.update_chat_ctx(ctx)

        if self._lk_session:
            self._lk_session.update_agent(market)
            await self._lk_session.say(
                "मी आपल्याला आमच्या कापूस बाजार आणि हमीभाव तज्ज्ञांकडे हस्तांतरित करत आहे. कृपया एक सेकंद थांबा.",
                allow_interruptions=True,
            )

        return "Transferred successfully to the Cotton Market & CCI procurement specialist."


class CottonPestSpecialist(Agent):
    """Cotton Pest & Disease Specialist Agent.
    Focuses strictly on insect/pest infestation and crop remedies.
    """

    def __init__(
        self,
        ctx: JobContext,
        caller_identity: str | None = None,
        start_time: float | None = None,
    ) -> None:
        self.ctx = ctx
        self.caller_identity = caller_identity
        self.user_id = caller_identity or "anonymous-phone"
        self.profile = {}
        self.start_time = start_time
        self.tool_executed = True
        self.error_log = None
        self._lk_session = None
        self._lk_ctx = ctx
        super().__init__(instructions=PEST_SPECIALIST_PROMPT)

    async def on_enter(self) -> None:
        logger.info("CottonPestSpecialist agent entered the session.")
        greeting = (
            "Namaskar, mee Krushi Mitra cha Cotton Pest Specialist ahe. "
            "Aapan कापसावरील कीड आणि रोग नियंत्रणाविषयी बोलत आहात. "
            "मी मागील संभाषण पाहिले आहे. सांगा दादा, काय समस्या आहे?"
        )
        if self.session:
            await self.session.say(greeting, allow_interruptions=True)

    @function_tool
    async def handoff_to_triage(self) -> str:
        """Call this tool if the farmer stops talking about pests/diseases and asks
        general questions about weather, registration, profile setup, or general greeting.
        This hands the call back to the main triage agent.
        """
        logger.info("Specialist handing back to Triage Agent...")
        triage = InboundAgent(
            ctx=self.ctx,
            caller_identity=self.caller_identity,
            start_time=self.start_time,
        )
        triage._lk_session = self.session
        triage._lk_ctx = self._lk_ctx
        triage.tool_executed = True

        # Copy context messages
        ctx = triage.chat_ctx.copy()
        for msg in self.chat_ctx.messages():
            ctx.add_message(role=msg.role, content=msg.content)
        await triage.update_chat_ctx(ctx)

        if self.session:
            self.session.update_agent(triage)
            await self.session.say(
                "मी आपल्याला आमच्या मुख्य सहाय्यकाकडे परत हस्तांतरित करत आहे.",
                allow_interruptions=True,
            )

        return "Transferred successfully back to the main Triage Agent."

    @function_tool
    async def handoff_to_market_specialist(self) -> str:
        """Call this tool if the farmer asks about MSP buying rates, CCI center location,
        Aadhaar/7/12 extract registration documents, or government procurement grading details.
        This hands the call over to the Cotton Market & CCI procurement specialist.
        """
        logger.info("Specialist handing over to Cotton Market Specialist...")
        market = CottonMarketSpecialist(
            ctx=self.ctx,
            caller_identity=self.caller_identity,
            start_time=self.start_time,
        )
        market._lk_session = self.session
        market._lk_ctx = self._lk_ctx
        market.tool_executed = True

        # Copy context messages
        ctx = market.chat_ctx.copy()
        for msg in self.chat_ctx.messages():
            ctx.add_message(role=msg.role, content=msg.content)
        await market.update_chat_ctx(ctx)

        if self.session:
            self.session.update_agent(market)
            await self.session.say(
                "मी आपल्याला आमच्या कापूस बाजार आणि हमीभाव तज्ज्ञांकडे हस्तांतरित करत आहे.",
                allow_interruptions=True,
            )

        return "Transferred successfully to the Cotton Market & CCI procurement specialist."

    @function_tool
    async def get_verified_pest_remedy(self, pest_name: str) -> str:
        """Call this tool immediately when the farmer asks for a remedy, chemical spray,
        preventive measures, or pesticide dosage details for any cotton crop pest or disease.
        This queries the database of government-approved agricultural advisories.
        """
        logger.info(f"RAG: Inbound querying verified advisory for pest: {pest_name}")
        advisory = await query_pest_advisory_async(pest_name)
        if advisory:
            logger.info(f"RAG: Found matching advisory for pest: {pest_name}")
            return (
                f"Verified Advisory for {pest_name}:\n"
                f"Advisory Details (Marathi): {advisory['advisory_text']}\n"
                f"Chemical Recommendation: {advisory['chemical_recommendation']}\n"
                f"Dosage Details: {advisory['dosage_details']}"
            )
        else:
            logger.warning(f"RAG: No advisory found for pest: {pest_name}")
            return "No verified government remedy found in the advisory database."


class CottonMarketSpecialist(Agent):
    """Cotton Market & CCI Procurement Specialist Agent.
    Focuses strictly on MSP purchasing centers, APMC mandi rates, and required documentation.
    """

    def __init__(
        self,
        ctx: JobContext,
        caller_identity: str | None = None,
        start_time: float | None = None,
    ) -> None:
        self.ctx = ctx
        self.caller_identity = caller_identity
        self.user_id = caller_identity or "anonymous-phone"
        self.profile = {}
        self.start_time = start_time
        self.tool_executed = True
        self.error_log = None
        self._lk_session = None
        self._lk_ctx = ctx
        super().__init__(instructions=MARKET_SPECIALIST_PROMPT)

    async def on_enter(self) -> None:
        logger.info("CottonMarketSpecialist agent entered the session.")
        greeting = (
            "Namaskar, mee Krushi Mitra cha Cotton Market Specialist ahe. "
            "Aapan कापूस हमीभाव आणि सीसीआय खरेदीबद्दल बोलत आहात. "
            "मी मागील संभाषण पाहिले आहे. सांगा, खरेदी केंद्राबद्दल काय माहिती हवी आहे?"
        )
        if self.session:
            await self.session.say(greeting, allow_interruptions=True)

    @function_tool
    async def handoff_to_triage(self) -> str:
        """Call this tool if the farmer stops talking about market rates/procurement and asks
        general questions about weather, registration, profile setup, or general greeting.
        This hands the call back to the main triage agent.
        """
        logger.info("Specialist handing back to Triage Agent...")
        triage = InboundAgent(
            ctx=self.ctx,
            caller_identity=self.caller_identity,
            start_time=self.start_time,
        )
        triage._lk_session = self.session
        triage._lk_ctx = self._lk_ctx
        triage.tool_executed = True

        # Copy context messages
        ctx = triage.chat_ctx.copy()
        for msg in self.chat_ctx.messages():
            ctx.add_message(role=msg.role, content=msg.content)
        await triage.update_chat_ctx(ctx)

        if self.session:
            self.session.update_agent(triage)
            await self.session.say(
                "मी आपल्याला आमच्या मुख्य सहाय्यकाकडे परत हस्तांतरित करत आहे.",
                allow_interruptions=True,
            )

        return "Transferred successfully back to the main Triage Agent."

    @function_tool
    async def handoff_to_pest_specialist(self) -> str:
        """Call this tool if the farmer asks about crop pests, insect infestation,
        pink bollworm, diseases, leaf curling, or pesticide spraying.
        This hands the call over to the Cotton Pest & Disease Specialist.
        """
        logger.info("Specialist handing over to Cotton Pest Specialist...")
        pest = CottonPestSpecialist(
            ctx=self.ctx,
            caller_identity=self.caller_identity,
            start_time=self.start_time,
        )
        pest._lk_session = self.session
        pest._lk_ctx = self._lk_ctx
        pest.tool_executed = True

        # Copy context messages
        ctx = pest.chat_ctx.copy()
        for msg in self.chat_ctx.messages():
            ctx.add_message(role=msg.role, content=msg.content)
        await pest.update_chat_ctx(ctx)

        if self.session:
            self.session.update_agent(pest)
            await self.session.say(
                "मी आपल्याला आमच्या कापूस कीड आणि रोग नियंत्रण तज्ज्ञांकडे हस्तांतरित करत आहे.",
                allow_interruptions=True,
            )

        return "Transferred successfully to the Cotton Pest & Disease Specialist."


# Bind the agent's internal HTTP health server to dynamic PORT (defaults to 8081)
server_port = int(os.getenv("PORT", "8081"))
server = AgentServer(port=server_port)


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load(
        activation_threshold=0.6, min_speech_duration=0.1
    )


server.setup_fnc = prewarm


def caller_phone_number(participant: rtc.RemoteParticipant) -> str | None:
    """The caller's phone number, if this participant arrived over SIP.

    LiveKit puts the caller ID in a participant attribute. Browser participants
    (i.e. anyone testing from the frontend) will not have it.
    """
    if participant.kind != rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
        return None
    return participant.attributes.get("sip.phoneNumber")


@server.rtc_session(agent_name="inbound-agent")
async def inbound_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Join the room first so we can read the caller's details before greeting them.
    await ctx.connect()
    participant = await ctx.wait_for_participant()

    phone_number = caller_phone_number(participant)
    user_id = phone_number or participant.identity
    logger.info(
        "inbound call answered",
        extra={"caller": phone_number or "unknown", "identity": participant.identity},
    )

    from database import async_get_farmer, async_get_last_call_summary, init_db

    init_db()

    profile = await async_get_farmer(user_id)
    last_summary = None
    if profile:
        last_summary = await async_get_last_call_summary(user_id)

    import time

    start_time = time.time()

    from agent import get_llm_provider, get_stt_provider

    session = AgentSession(
        stt=get_stt_provider(),
        llm=get_llm_provider(),
        tts=murf.TTS(
            voice=MURF_VOICE_ID,
            style="Conversational",
            model="GEN2",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=1),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(
            min_endpointing_delay=0.30, max_endpointing_delay=1.5
        ),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    agent_instance = InboundAgent(
        ctx=ctx,
        caller_identity=user_id,
        profile=profile,
        last_summary=last_summary,
        start_time=start_time,
    )
    agent_instance._lk_session = session
    agent_instance._lk_ctx = ctx

    await session.start(
        agent=agent_instance,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # BVCTelephony is tuned for the narrow frequency range of phone audio.
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    # Speak first — personalizing greeting if caller profile is known
    if profile and profile.get("name"):
        name = profile["name"]
        greeting = f"Namaskar {name} bhau, Krushi Mitra var tumche punha swagat ahe!"
        if last_summary:
            greeting += (
                " Maagchya veles aapan kelelya चर्चेबद्दल, aaj tumhala kaay madat pahije?"
            )
        else:
            greeting += " Aaj tumhala kaay madat karaychi ahe?"
    else:
        greeting = GREETING

    await session.say(greeting, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(server)
