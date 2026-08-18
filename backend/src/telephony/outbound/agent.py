"""Outbound telephony agent — places calls and talks to whoever answers.

Unlike the inbound agent, this one does the dialling. It waits to be dispatched
into a room with a phone number in the job metadata, then asks LiveKit to call
that number and bridge it into the room.

Run the worker with:

    uv run python src/telephony/outbound/agent.py dev

Then trigger a call from another terminal:

    uv run python src/telephony/outbound/dial.py --to +919999999999
"""

import asyncio
import json
import logging
import os

import aiohttp
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
from livekit.plugins import deepgram, murf, noise_cancellation, silero
from livekit.plugins import openai as lk_openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from prompts import SYSTEM_PROMPT

logger = logging.getLogger("outbound-agent")

load_dotenv(".env.local")

# Required — create this with `lk sip outbound create`
OUTBOUND_TRUNK_ID = os.getenv("LIVEKIT_SIP_OUTBOUND_TRUNK_ID")

# Optional — a phone number to transfer people to when they ask for a human.
TRANSFER_TO_NUMBER = os.getenv("TRANSFER_TO_NUMBER")

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MURF_VOICE_ID = os.getenv("MURF_VOICE_ID", "mr-IN-shilpa")
MURF_MODEL = "GEN2"

# The identity LiveKit gives the person we call. Used to transfer them later.
CALLEE_IDENTITY = "phone-user"


class OutboundAgent(Agent):
    def __init__(
        self,
        ctx: JobContext,
        user_id: str,
        profile: dict | None = None,
        last_summary: str | None = None,
    ) -> None:
        self.ctx = ctx
        self.user_id = user_id
        self.profile = profile or {}
        self.last_summary = last_summary
        self._lk_session = None
        self._lk_ctx = ctx

        # Build contextual instructions
        instructions = SYSTEM_PROMPT

        # Inject outbound purpose warning
        instructions = (
            f"[OUTBOUND CALL PURPOSE]\n"
            f"You are calling the farmer on their phone. State immediately that you are calling from Krushi Mitra "
            f"to deliver a warning or update about their cotton crops. Keep the call brief, respectful, and focused.\n\n"
            f"{instructions}"
        )

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
                f'Greet them warmly by name in Marathi: "Namaskar {name} bhau, Krushi Mitra varun bolat ahe!" '
                f"Reference their previous issues or crops if possible.\n\n"
            )
            instructions = returning_instruction + instructions

        super().__init__(instructions=instructions)

    @function_tool
    async def transfer_to_human(self, context: RunContext) -> str:
        """Transfer the person to a human colleague.

        Use this when they explicitly ask for a person, or when you cannot help
        them with their request.
        """
        if not TRANSFER_TO_NUMBER:
            return "Transfers are not available on this line. Offer to have someone call back instead."

        # Tell them before transferring — the SIP transfer cuts off the audio.
        await context.session.generate_reply(
            instructions="Tell them you're connecting them to a colleague now."
        )

        logger.info("transferring call to %s", TRANSFER_TO_NUMBER)
        try:
            await self.ctx.api.sip.transfer_sip_participant(
                api.TransferSIPParticipantRequest(
                    room_name=self.ctx.room.name,
                    participant_identity=CALLEE_IDENTITY,
                    transfer_to=f"tel:{TRANSFER_TO_NUMBER}",
                    play_dialtone=True,
                )
            )
        except Exception:
            logger.exception("transfer failed")
            return "The transfer did not go through. Apologize and offer a call back."

        return "Transferred."

    @function_tool
    async def detected_answering_machine(self, context: RunContext) -> str:
        """Hang up because the call reached a voicemail or answering machine.

        Use this as soon as you hear a recorded greeting rather than a live person.
        """
        logger.info("answering machine detected — hanging up")
        await self._hangup()
        return "Call ended."

    @function_tool
    async def end_call(self, context: RunContext) -> str:
        """Hang up the call.

        Use this once the conversation is finished and you have said goodbye.
        """
        await context.session.generate_reply(
            instructions="Thank them for their time and say a short goodbye."
        )

        logger.info("ending call")
        await self._hangup()
        return "Call ended."

    async def _hangup(self) -> None:
        """Delete the room, which drops the SIP leg and ends the phone call."""
        await self.ctx.api.room.delete_room(
            api.DeleteRoomRequest(room=self.ctx.room.name)
        )

    async def on_session_end(self) -> None:
        """Save call summary to SQLite when outbound call ends."""
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
                        "Summarize this outbound warning/advisory call with a cotton farmer in Marathi. "
                        "Make it 1 to 2 sentences. Focus on what warning was delivered and what the farmer said. "
                        "Do not include greeting or conversational filler. Keep it strictly factual.\n\n"
                        f"Conversation:\n{dialogue_text}"
                    )

                    ctx = ChatContext()
                    ctx.add_message(role="user", content=summary_prompt)

                    response = await llm.chat(chat_ctx=ctx).collect()
                    summary_text = response.text.strip()

                    if summary_text:
                        from database import save_call_summary

                        save_call_summary(self.user_id, summary_text)
                        logger.info(
                            "Saved outbound call summary for %s: %s",
                            self.user_id,
                            summary_text,
                        )
                except Exception as e:
                    logger.error(
                        "Failed to generate or save outbound call summary: %s", e
                    )

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
        coords = {
            "yavatmal": (20.389, 78.131),
            "amravati": (20.932, 77.752),
            "akola": (20.700, 77.008),
            "wardha": (20.745, 78.602),
        }

        cleaned_district = district.strip().lower()
        if cleaned_district not in coords:
            logger.warning(
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
                return f"Live 3-day weather forecast for {target_name} (retrieved today):\n{forecast_str}"

        except asyncio.TimeoutError:
            logger.error("Weather API call timed out.")
            return "Error: The live weather service timed out. Please tell the farmer that the weather system is temporarily busy, and recommend checking rain signs manually."
        except Exception as e:
            logger.error("Weather API failed with exception: %s", e)
            return "Error: Failed to connect to the weather service due to a technical error."

    @function_tool
    async def get_cotton_mandi_prices(self, district: str) -> str:
        """Fetch the cotton mandi (APMC) market prices for a specific district in Vidarbha (Yavatmal, Amravati, Akola, Wardha).

        Parameters:
        - district: The district name (e.g., 'Yavatmal', 'Amravati', 'Akola', 'Wardha').

        Use this when the farmer asks about cotton rates, market prices, or mandi rates.
        """
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
            mandi_file = os.path.join(
                os.path.dirname(__file__), "..", "..", "mandi_prices.json"
            )
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

            return (
                f"Cotton rates for {mandi_name} from yesterday's close (August 16, 2026):\n"
                f"- Minimum price: {min_price} rupees per quintal\n"
                f"- Maximum price: {max_price} rupees per quintal\n"
                f"- Average modal price: {modal_price} rupees per quintal\n"
                f"- Reference Government MSP: {msp_ref} rupees per quintal."
            )
        except Exception as e:
            logger.error("Failed to load cotton mandi prices: %s", e)
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
            logger.info(
                "Created outbound escalation ticket #%s for user %s: %s (Urgency: %s)",
                ticket_id,
                self.user_id,
                reason,
                urgency,
            )
            return (
                f"Successfully created escalation ticket #{ticket_id}. "
                f"Please tell the farmer that their ticket number is {ticket_id} and "
                f"a KVK specialist will call them back on this number soon."
            )
        except Exception as e:
            logger.error("Failed to create escalation ticket: %s", e)
            return "Error: Could not create escalation ticket due to an internal server error."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


def phone_number_from_metadata(ctx: JobContext) -> str | None:
    """Read the number to dial out of the dispatch metadata set by dial.py."""
    metadata = ctx.job.metadata
    if not metadata:
        return None
    try:
        return json.loads(metadata).get("phone_number")
    except json.JSONDecodeError:
        return metadata.strip() or None


@server.rtc_session(agent_name="outbound-agent")
async def outbound_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    phone_number = phone_number_from_metadata(ctx)
    if not phone_number:
        logger.error(
            "no phone number in job metadata — dispatch with "
            '{"phone_number": "+919999999999"}'
        )
        ctx.shutdown()
        return

    # 1. Query database for profile and last call history
    from database import get_farmer, get_last_call_summary, init_db

    init_db()

    profile = get_farmer(phone_number)
    last_summary = get_last_call_summary(phone_number)

    # 2. Instantiate OutboundAgent with contextual data
    agent_instance = OutboundAgent(
        ctx=ctx, user_id=phone_number, profile=profile, last_summary=last_summary
    )

    await ctx.connect()

    # 3. Same voice pipeline as src/agent.py
    session = AgentSession(
        # STT: Deepgram Nova-3 multilingual
        stt=deepgram.STT(model="nova-3", language="multi"),
        # LLM: Groq
        llm=lk_openai.LLM(
            model=GROQ_MODEL,
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
        ),
        # TTS: Murf Falcon 2 Marathi voice
        tts=murf.TTS(
            voice=MURF_VOICE_ID,
            style="Conversational",
            model=MURF_MODEL,
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    # Link session and ctx back to the agent instance
    agent_instance._lk_session = session
    agent_instance._lk_ctx = ctx

    # 4. Start the session while the phone is ringing
    session_started = asyncio.create_task(
        session.start(
            agent=agent_instance,
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=lambda params: (
                        noise_cancellation.BVCTelephony()
                        if params.participant.kind
                        == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                        else noise_cancellation.BVC()
                    ),
                ),
            ),
        )
    )

    logger.info("dialing %s", phone_number)
    try:
        if not OUTBOUND_TRUNK_ID:
            # For testing logic without a trunk, we trigger room-join manually or mock.
            # In live: raise error so it doesn't try to call empty trunk.
            raise ValueError("LIVEKIT_SIP_OUTBOUND_TRUNK_ID is not configured.")

        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=OUTBOUND_TRUNK_ID,
                sip_call_to=phone_number,
                participant_identity=CALLEE_IDENTITY,
                participant_name="Phone user",
                wait_until_answered=True,
            )
        )
    except Exception as e:
        logger.error("dialing %s failed: %s", phone_number, e)
        session_started.cancel()
        ctx.shutdown()
        return

    await session_started

    # 5. Dynamic Marathi Outbound Greeting
    if profile and profile.get("name"):
        name = profile["name"]
        greeting = f"Namaskar {name} bhau, Mee Krushi Mitra bolat ahe. Aplya cotton crop sathi mhatvacha havaman andaz aala ahe. Aata bolu shakto ka?"
    else:
        greeting = "Namaskar! Mee Krushi Mitra bolat ahe. Aplya cotton crop sathi mhatvacha andaz aala ahe. Aata bolu shakto ka?"

    await session.say(greeting, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(server)
