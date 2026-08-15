"""
Tests for Krushi Mitra system prompt.
These tests verify that the prompt enforces the correct guardrails, persona,
language settings, and spoken-voice formatting rules.

Tests are purely logic-based — no LLM calls, no API calls.
Run with: uv run pytest tests/test_prompts.py -v
"""

from prompts import AGENT_NAME, AGENT_TAGLINE_EN, SYSTEM_PROMPT


class TestAgentIdentity:
    """Verify the agent's name and domain are correctly embedded in the prompt."""

    def test_agent_name_is_krushi_mitra(self):
        """Prompt must identify the agent as 'Krushi Mitra'."""
        assert "Krushi Mitra" in SYSTEM_PROMPT, (
            "Agent must identify itself as 'Krushi Mitra' in the system prompt."
        )

    def test_agent_name_constant(self):
        """AGENT_NAME constant must match expected value."""
        assert AGENT_NAME == "Krushi Mitra"

    def test_tagline_exists(self):
        """English tagline must exist and reference Vidarbha."""
        assert "Vidarbha" in AGENT_TAGLINE_EN

    def test_domain_scope_vidarbha(self):
        """Prompt must scope the agent to Vidarbha region."""
        assert "Vidarbha" in SYSTEM_PROMPT, (
            "Prompt must mention Vidarbha to keep the agent domain-scoped."
        )

    def test_domain_scope_cotton(self):
        """Prompt must explicitly cover cotton (kapas) farming."""
        assert "kapas" in SYSTEM_PROMPT.lower() or "cotton" in SYSTEM_PROMPT.lower(), (
            "Prompt must mention cotton/kapas as the primary crop domain."
        )

    def test_target_districts_mentioned(self):
        """At least one Vidarbha district must be named to anchor the geography."""
        districts = ["Yavatmal", "Amravati", "Akola", "Wardha"]
        found = [d for d in districts if d in SYSTEM_PROMPT]
        assert len(found) >= 1, (
            f"Prompt must mention at least one Vidarbha district. None of {districts} found."
        )


class TestSpokenVoiceFormatting:
    """Verify the prompt enforces spoken-voice-safe formatting rules."""

    def test_no_markdown_instruction(self):
        """Prompt must explicitly forbid markdown/bullet formatting."""
        keywords = ["bullet", "markdown", "asterisk", "numbered list"]
        found = [k for k in keywords if k in SYSTEM_PROMPT.lower()]
        assert len(found) >= 1, (
            f"Prompt must forbid markdown formatting for voice output. "
            f"None of {keywords} found in prompt."
        )

    def test_sentence_length_guidance(self):
        """Prompt must include guidance on sentence/response length for voice."""
        assert any(
            term in SYSTEM_PROMPT.lower()
            for term in ["sentence", "words", "short", "concise", "15"]
        ), "Prompt must include guidance on keeping responses short for voice output."


class TestOpeningGreeting:
    """Verify the opening greeting is in Marathi and present in the prompt."""

    def test_opening_greeting_present(self):
        """Prompt must include a specific Marathi opening greeting."""
        assert "Namaskar" in SYSTEM_PROMPT, (
            "Prompt must include a Marathi opening greeting with 'Namaskar'."
        )

    def test_opening_greeting_identifies_agent(self):
        """Opening greeting must state the agent's name."""
        assert "Krushi Mitra" in SYSTEM_PROMPT and "Namaskar" in SYSTEM_PROMPT, (
            "Opening greeting must include both 'Namaskar' and 'Krushi Mitra'."
        )


class TestCallObjectives:
    """Verify Day 2 formal call objectives are present."""

    def test_objectives_section_exists(self):
        assert "[OBJECTIVES]" in SYSTEM_PROMPT

    def test_objective_bond_ali_awareness(self):
        assert "Bond Ali" in SYSTEM_PROMPT or "Pink bollworm" in SYSTEM_PROMPT

    def test_objective_msp_guidance(self):
        assert "MSP" in SYSTEM_PROMPT and "CCI" in SYSTEM_PROMPT

    def test_objective_pmfby_guidance(self):
        assert "PMFBY" in SYSTEM_PROMPT and "claim" in SYSTEM_PROMPT.lower()


class TestGuardrailRedTeam:
    """Day 2 Red-Team Guardrail tests.
    Verifies the prompt explicitly instructs the LLM on how to handle adversarial or out-of-bounds requests.
    """

    def test_rt_price_claim(self):
        """Verifies agent is instructed to refuse stating live market prices."""
        assert "Never state a market price" in SYSTEM_PROMPT
        assert "Mala aajche bhaav mahit nahi" in SYSTEM_PROMPT

    def test_rt_pesticide_dose(self):
        """Verifies agent is instructed not to recommend specific pesticide brands."""
        assert "Never recommend a specific pesticide brand" in SYSTEM_PROMPT
        assert "KVK" in SYSTEM_PROMPT

    def test_rt_scheme_approval(self):
        """Verifies agent is instructed never to promise scheme approval."""
        assert "Never claim a scheme application" in SYSTEM_PROMPT
        assert "approved" in SYSTEM_PROMPT.lower()

    def test_rt_aadhaar_warning(self):
        """Verifies agent is instructed to stop and warn if Aadhaar is revealed."""
        assert "Aadhaar" in SYSTEM_PROMPT
        assert "stop" in SYSTEM_PROMPT.lower() and "warn" in SYSTEM_PROMPT.lower()

    def test_rt_otp_refusal(self):
        """Verifies agent is instructed never to ask/store OTP."""
        assert "OTP" in SYSTEM_PROMPT
        assert "store" in SYSTEM_PROMPT.lower()

    def test_rt_all_clear_crop(self):
        """Verifies agent is instructed never to issue an all-clear."""
        assert (
            "all-clear" in SYSTEM_PROMPT.lower()
            or "guarantee crop safety" in SYSTEM_PROMPT.lower()
        )

    def test_rt_distress_trigger(self):
        """Verifies distress helpline escalation exists."""
        assert (
            "suicidal" in SYSTEM_PROMPT.lower() or "distress" in SYSTEM_PROMPT.lower()
        )
        assert "1800-599-0019" in SYSTEM_PROMPT

    def test_rt_fake_weather(self):
        """Verifies agent is instructed to refuse stating weather forecast without source."""
        assert "weather forecast" in SYSTEM_PROMPT.lower()
        assert "Mala aajcha havaman andaz mahit nahi" in SYSTEM_PROMPT

    def test_rt_insurance_payout(self):
        """Verifies agent is instructed never to state exact insurance payout amounts."""
        assert "exact crop insurance payout amounts" in SYSTEM_PROMPT.lower()

    def test_rt_honesty_unknown(self):
        """Verifies agent is instructed to be honest when it doesn't know."""
        assert any(
            term in SYSTEM_PROMPT
            for term in ["Mala naahi", "don't know", "I do not know", "naahi mahit"]
        )
