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

    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self._latency = LatencyTracker()

    async def on_user_speech_committed(self, message) -> None:
        """Called when user finishes speaking — start latency clock."""
        self._latency.on_speech_end()
        app_logger.debug("[TURN] User speech committed: %s", message.content[:60])

    async def on_agent_speech_started(self) -> None:
        """Called when TTS first audio chunk is ready — record latency."""
        self._latency.on_tts_first_audio()
        self._latency.log_turn()

    async def on_session_end(self) -> None:
        """Log full session latency summary when conversation ends."""
        summary = self._latency.summary()
        app_logger.info("[SESSION END] Latency summary: %s", summary)


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

    await session.start(
        agent=KrushiMitra(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    # Telephony-optimized for SIP callers (future days)
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    await ctx.connect()
    app_logger.info("Krushi Mitra connected. Ready for farmer queries.")


if __name__ == "__main__":
    cli.run_app(server)
