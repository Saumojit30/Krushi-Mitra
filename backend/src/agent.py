"""
Krushi Mitra — Main Voice Agent
Cotton Farmer Advisory | Vidarbha, Maharashtra | Track: Farm & Field
Day 1: Foundation — voice pipeline with Marathi Murf Falcon 2 TTS + Groq LLM
"""

import logging
import os

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.plugins import deepgram, murf, noise_cancellation, silero
from livekit.plugins import openai as lk_openai  # Groq uses OpenAI-compatible API
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from logger import LatencyTracker
from prompts import (
    AGENT_NAME,
    MARKET_SPECIALIST_PROMPT,
    PEST_SPECIALIST_PROMPT,
    SYSTEM_PROMPT,
)
from rag_utility import query_pest_advisory

# Load env variables from .env.local (never committed to git)
load_dotenv(".env.local")

app_logger = logging.getLogger("krushi_mitra")

# ---------------------------------------------------------------------------
# Groq configuration (OpenAI-compatible endpoint)
# Model: openai/gpt-oss-20b is the safe non-deprecated choice as of Aug 2026
# Fallback: llama-3.3-70b-versatile
# ---------------------------------------------------------------------------
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ---------------------------------------------------------------------------
# Murf Falcon 2 Marathi voice
# Falcon 2 is the current non-deprecated model as of Aug 16, 2026
# Voice ID is set via env var — see .env.example for how to find it
# ---------------------------------------------------------------------------
MURF_VOICE_ID = os.getenv(
    "MURF_VOICE_ID", "mr-IN-shilpa"
)  # placeholder — set real ID in .env.local
MURF_MODEL = "GEN2"  # Falcon 2 — do NOT use GEN1, deprecated Aug 16 2026


class KrushiMitra(Agent):
    """
    Krushi Mitra voice agent.
    Serves cotton farmers in Vidarbha (Yavatmal, Amravati, Akola, Wardha).
    Primary language: Marathi. Fallback: Hindi.
    """

    def __init__(
        self,
        user_id: str = "test-user",
        profile: dict | None = None,
        last_summary: str | None = None,
        start_time: float | None = None,
    ) -> None:
        self.user_id = user_id
        self.profile = profile or {}
        self.last_summary = last_summary
        self._latency = LatencyTracker()
        self._lk_session = None
        self._lk_ctx = None
        self.start_time = start_time
        self.tool_executed = False
        self.error_log = None

        # Build contextual system prompt instructions
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

    async def on_user_speech_committed(self, message) -> None:
        """Called when user finishes speaking — start latency clock."""
        self._latency.on_speech_end()
        app_logger.debug("[TURN] User speech committed: %s", message.content[:60])

    async def on_agent_speech_started(self) -> None:
        """Called when TTS first audio chunk is ready — record latency."""
        self._latency.on_tts_first_audio()
        self._latency.log_turn()

    async def on_session_end(self) -> None:
        """Log latency and save call summary + analytics to database."""
        import time

        summary = self._latency.summary()
        app_logger.info("[SESSION END] Latency summary: %s", summary)

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
                        "Summarize this conversation with a cotton farmer in Marathi. "
                        "Make it 1 to 2 sentences. Focus only on the farming issues raised and the advice given. "
                        "Do not include greeting or conversational filler. Keep it strictly factual.\n\n"
                        f"Conversation:\n{dialogue_text}"
                    )

                    ctx = ChatContext()
                    ctx.add_message(role="user", content=summary_prompt)

                    response = await llm.chat(chat_ctx=ctx).collect()
                    summary_text = response.text.strip()

                    if summary_text:
                        from database import save_call_summary

                        save_call_summary(
                            self.user_id,
                            summary_text,
                            duration_seconds=duration,
                            outcome=outcome,
                            error_log=error_msg,
                            call_type="INBOUND",
                        )
                        app_logger.info(
                            "Saved conversation summary for %s: %s (Duration: %ss, Outcome: %s)",
                            self.user_id,
                            summary_text,
                            duration,
                            outcome,
                        )
                except Exception as e:
                    app_logger.error("Failed to generate or save call summary: %s", e)
            else:
                try:
                    from database import save_call_summary

                    save_call_summary(
                        self.user_id,
                        "Call connected but no dialogue took place.",
                        duration_seconds=duration,
                        outcome="FAILURE",
                        error_log="No dialogue detected",
                        call_type="INBOUND",
                    )
                except Exception as e:
                    app_logger.error("Failed to save failed call log: %s", e)

    @function_tool
    async def get_farmer_profile(self) -> str:
        """Retrieve the farmer's profile including name, crop, location, and irrigation details.

        Use this at the beginning of the call if you need to double-check their records.
        """
        from database import get_farmer

        profile = get_farmer(self.user_id)
        if profile:
            return f"Farmer Profile: {profile}"
        return "No profile found for this caller."

    @function_tool
    async def save_farmer_profile(
        self,
        name: str | None = None,
        crops_grown: str | None = None,
        land_size_acres: float | None = None,
        district: str | None = None,
        irrigation_type: str | None = None,
        consent_given: bool = False,
    ) -> str:
        """Save or update the farmer's profile information.

        Parameters:
        - name: The farmer's name.
        - crops_grown: The crops they grow (e.g., 'cotton').
        - land_size_acres: The size of their farm in acres.
        - district: The district they reside in (e.g., 'Yavatmal', 'Amravati').
        - irrigation_type: Their farm's irrigation type (e.g., 'rainfed', 'drip').
        - consent_given: True if the farmer explicitly agreed to save this information.

        IMPORTANT: You must ask the farmer for permission before calling this tool.
        If they say no, do not call this tool. If they say yes, set consent_given=True.
        """
        if not consent_given:
            return (
                "Error: You must ask the farmer for explicit permission before saving their details. "
                "Ask 'Is it okay if I remember your details for next time?' and call this tool only if they agree."
            )

        from database import save_farmer

        facts = {}
        if crops_grown is not None:
            facts["crops_grown"] = crops_grown
        if land_size_acres is not None:
            facts["land_size_acres"] = land_size_acres
        if district is not None:
            facts["district"] = district
        if irrigation_type is not None:
            facts["irrigation_type"] = irrigation_type

        save_farmer(user_id=self.user_id, name=name, facts=facts)
        self.tool_executed = True
        return "Profile successfully saved/updated."

    @function_tool
    async def get_last_call_summary(self) -> str:
        """Retrieve a summary of the last conversation with this farmer."""
        from database import get_last_call_summary

        summary = get_last_call_summary(self.user_id)
        if summary:
            return f"Last call summary: {summary}"
        return "No previous call history found."

    @function_tool
    async def get_weather_forecast(self, district: str) -> str:
        """Fetch the 3-day weather forecast (including precipitation probability and max/min temperatures) for a specific district in Vidarbha (Yavatmal, Amravati, Akola, Wardha).

        Parameters:
        - district: The district name (e.g., 'Yavatmal', 'Amravati', 'Akola', 'Wardha').

        Use this when the farmer asks about rain, temperature, or weather forecasts.
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
            app_logger.warning(
                "Unrecognized district requested for weather: %s. Defaulting to Yavatmal.",
                district,
            )
            lat, lon = coords["yavatmal"]
            target_name = "Yavatmal (default)"
        else:
            lat, lon = coords[cleaned_district]
            target_name = district.strip().capitalize()

        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&daily=precipitation_probability_max,temperature_2m_max,temperature_2m_min"
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
                return f"Live 3-day weather forecast for {target_name} (retrieved today):\n{forecast_str}"

        except asyncio.TimeoutError:
            app_logger.error("Weather API call timed out.")
            self.error_log = "Weather API call timed out"
            return "Error: The live weather service timed out. Please tell the farmer that the weather system is temporarily busy, and recommend checking rain signs manually."
        except Exception as e:
            app_logger.error("Weather API failed with exception: %s", e)
            self.error_log = f"Weather API failed with exception: {e}"
            return "Error: Failed to connect to the weather service due to a technical error."

    @function_tool
    async def get_cotton_mandi_prices(self, district: str) -> str:
        """Fetch the cotton mandi (APMC) market prices for a specific district in Vidarbha (Yavatmal, Amravati, Akola, Wardha).

        Parameters:
        - district: The district name (e.g., 'Yavatmal', 'Amravati', 'Akola', 'Wardha').

        Use this when the farmer asks about cotton rates, market prices, or mandi rates.
        """
        import json
        import os

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
            mandi_file = os.path.join(os.path.dirname(__file__), "mandi_prices.json")
            if not os.path.exists(mandi_file):
                return "Error: Mandi prices dataset is missing."

            with open(mandi_file) as f:
                data = json.load(f)

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
            app_logger.error("Failed to load cotton mandi prices: %s", e)
            self.error_log = f"Failed to load cotton mandi prices: {e}"
            return (
                "Error: Could not retrieve market prices due to a local server error."
            )

    @function_tool
    async def create_escalation(self, reason: str, summary: str, urgency: str) -> str:
        """Create an escalation ticket to a human agricultural specialist (KVK Officer).

        Parameters:
        - reason: The primary reason for escalation (e.g., 'Severe Pink Bollworm infestation', 'Pesticide brand recommendation request', 'Mandi price dispute').
        - summary: A concise summary of the issue (Who, what happened, what was checked). DO NOT include private passwords, PINs, or OTPs.
        - urgency: The level of urgency ('HIGH' or 'MEDIUM').

        Use this only when the farmer has explicitly agreed to escalate.
        """
        try:
            from database import create_escalation

            ticket_id = create_escalation(
                user_id=self.user_id,
                reason=reason,
                summary=summary,
                urgency=urgency,
            )
            app_logger.info(
                "Created escalation ticket #%s for user %s: %s (Urgency: %s)",
                ticket_id,
                self.user_id,
                reason,
                urgency,
            )
            self.tool_executed = True
            return (
                f"Successfully created escalation ticket #{ticket_id}. "
                f"Please tell the farmer that their ticket number is {ticket_id} and "
                f"a KVK specialist will call them back on this number soon."
            )
        except Exception as e:
            app_logger.error("Failed to create escalation ticket: %s", e)
            self.error_log = f"Failed to create escalation ticket: {e}"
            return "Error: Could not create escalation ticket due to an internal server error."

    @function_tool
    async def handoff_to_pest_specialist(self) -> str:
        """Call this tool immediately when the farmer asks questions about crop pests,
        insect infestation, pink bollworm, crop diseases, plant damage, or pesticide spraying.
        This hands the call over to the specialized Cotton Pest & Disease Specialist.
        """
        app_logger.info("Triage handing over to Cotton Pest Specialist...")
        pest = CottonPestSpecialist(
            user_id=self.user_id,
            profile=self.profile,
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
        app_logger.info("Triage handing over to Cotton Market Specialist...")
        market = CottonMarketSpecialist(
            user_id=self.user_id,
            profile=self.profile,
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
        user_id: str = "test-user",
        profile: dict | None = None,
        start_time: float | None = None,
    ) -> None:
        self.user_id = user_id
        self.profile = profile or {}
        self.start_time = start_time
        self.tool_executed = True  # Routing to a specialist is an advisory action
        self.error_log = None
        self._lk_session = None
        self._lk_ctx = None
        super().__init__(instructions=PEST_SPECIALIST_PROMPT)

    async def on_enter(self) -> None:
        app_logger.info("CottonPestSpecialist agent entered the session.")
        greeting = (
            "Namaskar, mee Krushi Mitra cha Cotton Pest Specialist ahe. "
            "Aapan कापसावरील कीड आणि रोग नियंत्रणाविषयी बोलत आहात. "
            "मी मागील संभाषण पाहिले आहे. सांगा दादा, काय समस्या आहे?"
        )
        if self._lk_session:
            await self._lk_session.say(greeting, allow_interruptions=True)

    @function_tool
    async def handoff_to_triage(self) -> str:
        """Call this tool if the farmer stops talking about pests/diseases and asks
        general questions about weather, registration, profile setup, or general greeting.
        This hands the call back to the main triage agent.
        """
        app_logger.info("Specialist handing back to Triage Agent...")
        triage = KrushiMitra(
            user_id=self.user_id,
            profile=self.profile,
            start_time=self.start_time,
        )
        # Link session and context
        triage._lk_session = self._lk_session
        triage._lk_ctx = self._lk_ctx
        triage.tool_executed = True

        # Copy context messages
        ctx = triage.chat_ctx.copy()
        for msg in self.chat_ctx.messages():
            ctx.add_message(role=msg.role, content=msg.content)
        await triage.update_chat_ctx(ctx)

        if self._lk_session:
            self._lk_session.update_agent(triage)
            await self._lk_session.say(
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
        app_logger.info("Specialist handing over to Cotton Market Specialist...")
        market = CottonMarketSpecialist(
            user_id=self.user_id,
            profile=self.profile,
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
        app_logger.info(f"RAG: Querying verified advisory for pest: {pest_name}")
        advisory = query_pest_advisory(pest_name)
        if advisory:
            app_logger.info(f"RAG: Found matching advisory for pest: {pest_name}")
            return (
                f"Verified Advisory for {pest_name}:\n"
                f"Advisory Details (Marathi): {advisory['advisory_text']}\n"
                f"Chemical Recommendation: {advisory['chemical_recommendation']}\n"
                f"Dosage Details: {advisory['dosage_details']}"
            )
        else:
            app_logger.warning(f"RAG: No advisory found for pest: {pest_name}")
            return "No verified government remedy found in the advisory database."


class CottonMarketSpecialist(Agent):
    """Cotton Market & CCI Procurement Specialist Agent.
    Focuses strictly on MSP purchasing centers, APMC mandi rates, and required documentation.
    """

    def __init__(
        self,
        user_id: str = "test-user",
        profile: dict | None = None,
        start_time: float | None = None,
    ) -> None:
        self.user_id = user_id
        self.profile = profile or {}
        self.start_time = start_time
        self.tool_executed = True  # Routing to a specialist is an advisory action
        self.error_log = None
        self._lk_session = None
        self._lk_ctx = None
        super().__init__(instructions=MARKET_SPECIALIST_PROMPT)

    async def on_enter(self) -> None:
        app_logger.info("CottonMarketSpecialist agent entered the session.")
        greeting = (
            "Namaskar, mee Krushi Mitra cha Cotton Market Specialist ahe. "
            "Aapan कापूस हमीभाव आणि सीसीआय खरेदीबद्दल बोलत आहात. "
            "मी मागील संभाषण पाहिले आहे. सांगा, खरेदी केंद्राबद्दल काय माहिती हवी आहे?"
        )
        if self._lk_session:
            await self._lk_session.say(greeting, allow_interruptions=True)

    @function_tool
    async def handoff_to_triage(self) -> str:
        """Call this tool if the farmer stops talking about market rates/procurement and asks
        general questions about weather, registration, profile setup, or general greeting.
        This hands the call back to the main triage agent.
        """
        app_logger.info("Specialist handing back to Triage Agent...")
        triage = KrushiMitra(
            user_id=self.user_id,
            profile=self.profile,
            start_time=self.start_time,
        )
        triage._lk_session = self._lk_session
        triage._lk_ctx = self._lk_ctx
        triage.tool_executed = True

        # Copy context messages
        ctx = triage.chat_ctx.copy()
        for msg in self.chat_ctx.messages():
            ctx.add_message(role=msg.role, content=msg.content)
        await triage.update_chat_ctx(ctx)

        if self._lk_session:
            self._lk_session.update_agent(triage)
            await self._lk_session.say(
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
        app_logger.info("Specialist handing over to Cotton Pest Specialist...")
        pest = CottonPestSpecialist(
            user_id=self.user_id,
            profile=self.profile,
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
                "मी आपल्याला आमच्या कापूस कीड आणि रोग नियंत्रण तज्ज्ञांकडे हस्तांतरित करत आहे.",
                allow_interruptions=True,
            )

        return "Transferred successfully to the Cotton Pest & Disease Specialist."


server = AgentServer()


def prewarm(proc: JobProcess):
    """Pre-warm the VAD model before first call."""
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="krushi-mitra")
async def krushi_mitra_session(ctx: JobContext):
    """
    Main voice pipeline session for Krushi Mitra.
    STT: Deepgram Nova-3 (multilingual, handles Marathi + Hindi)
    LLM: Groq (OpenAI-compatible, fast inference, non-deprecated model)
    TTS: Murf Falcon 2 (Marathi voice, low-latency)
    """
    ctx.log_context_fields = {
        "room": ctx.room.name,
        "agent": AGENT_NAME,
    }

    app_logger.info("Krushi Mitra session starting for room: %s", ctx.room.name)

    # 1. Connect and retrieve participant information
    await ctx.connect()
    participant = await ctx.wait_for_participant()

    # Resolve caller phone number or default to test ID
    phone_number = None
    if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
        phone_number = participant.attributes.get("sip.phoneNumber")
    else:
        phone_number = "browser-test-user"

    app_logger.info("Caller identified: %s", phone_number)

    # 2. Query database for profile and last call history
    from database import get_farmer, get_last_call_summary, init_db

    init_db()

    profile = get_farmer(phone_number)
    last_summary = get_last_call_summary(phone_number)

    # 3. Instantiate KrushiMitra agent with contextual data
    agent_instance = KrushiMitra(
        user_id=phone_number, profile=profile, last_summary=last_summary
    )

    # 4. Set up voice pipeline session
    session = AgentSession(
        # STT: Deepgram Nova-3 — supports Marathi and Hindi in multilingual mode
        stt=deepgram.STT(model="nova-3", language="multi"),
        # LLM: Groq via OpenAI-compatible API
        # Groq base_url points to api.groq.com, model = llama-3.3-70b-versatile
        llm=lk_openai.LLM(
            model=GROQ_MODEL,
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
        ),
        # TTS: Murf Falcon 2 — Marathi voice
        tts=murf.TTS(
            voice=MURF_VOICE_ID,
            style="Conversational",
            model=MURF_MODEL,
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        # Turn detection: Multilingual model handles Marathi/Hindi code-switching
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # Preemptive generation reduces perceived latency
        preemptive_generation=True,
    )

    # Link session and ctx back to the agent instance for summaries and callbacks
    agent_instance._lk_session = session
    agent_instance._lk_ctx = ctx

    # 5. Start the session
    import time

    if not agent_instance.start_time:
        agent_instance.start_time = time.time()
    await session.start(
        agent=agent_instance,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    # Telephony-optimized for SIP callers
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    # 6. Generate and speak dynamic greeting (starts the conversation immediately)
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
        greeting = "Namaskar! Mee Krushi Mitra — Vidarbhyatil kapas shetkaryasathi. Aaj tumhala kaay madat karaychi ahe?"

    await session.say(greeting, allow_interruptions=True)
    app_logger.info("Krushi Mitra connected and greeted user.")


if __name__ == "__main__":
    cli.run_app(server)
