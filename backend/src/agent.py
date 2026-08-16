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
from prompts import AGENT_NAME, SYSTEM_PROMPT

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
    ) -> None:
        self.user_id = user_id
        self.profile = profile or {}
        self.last_summary = last_summary
        self._latency = LatencyTracker()
        self._lk_session = None
        self._lk_ctx = None

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
        """Log latency and save call summary to database."""
        summary = self._latency.summary()
        app_logger.info("[SESSION END] Latency summary: %s", summary)

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

                        save_call_summary(self.user_id, summary_text)
                        app_logger.info(
                            "Saved conversation summary for %s: %s",
                            self.user_id,
                            summary_text,
                        )
                except Exception as e:
                    app_logger.error("Failed to generate or save call summary: %s", e)

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
