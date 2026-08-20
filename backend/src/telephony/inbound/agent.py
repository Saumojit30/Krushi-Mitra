"""Inbound telephony agent — answers incoming phone calls.

A caller dials your phone number, your SIP provider forwards the call to LiveKit,
and LiveKit's dispatch rule routes it to this agent by name ("inbound-agent").

Run it with:

    uv run python src/telephony/inbound/agent.py dev

See src/telephony/README.md for the trunk and dispatch rule setup.
"""

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
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from prompts import MARKET_SPECIALIST_PROMPT, PEST_SPECIALIST_PROMPT

logger = logging.getLogger("inbound-agent")

load_dotenv(".env.local")

# Optional — a phone number to transfer callers to when they ask for a human.
# Leave unset and the transfer tool politely declines instead.
TRANSFER_TO_NUMBER = os.getenv("TRANSFER_TO_NUMBER")

# Change this prompt to change what your phone agent does.
SYSTEM_PROMPT = """You are a friendly receptionist answering calls for a small business. Help callers with questions about hours, services, and locations, and take messages when needed. You are speaking on a phone call, so keep responses short and conversational — no formatting, emojis, or symbols. If the caller asks for a human, use the transfer_to_human tool. When the conversation is finished and the caller says goodbye, use the end_call tool."""

# The first thing the caller hears when they pick up.
GREETING = "Thanks for calling! How can I help you today?"


class InboundAgent(Agent):
    def __init__(
        self,
        ctx: JobContext,
        caller_identity: str | None,
        start_time: float | None = None,
    ) -> None:
        self.ctx = ctx
        self.caller_identity = caller_identity
        self.user_id = caller_identity or "anonymous-phone"
        self.profile = {}
        self.start_time = start_time
        self._lk_session = None
        self._lk_ctx = ctx
        self.tool_executed = False
        self.error_log = None
        super().__init__(instructions=SYSTEM_PROMPT)

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


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


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
    logger.info(
        "inbound call answered",
        extra={"caller": phone_number or "unknown", "identity": participant.identity},
    )

    # Same voice pipeline as src/agent.py — see that file for the annotated version.
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(
            model="gemini-2.5-flash",
        ),
        tts=murf.TTS(
            voice="en-US-matthew",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    await session.start(
        agent=InboundAgent(ctx, participant.identity),
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

    # Speak first — the caller dialled you, so they expect to be greeted.
    await session.say(GREETING, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(server)
