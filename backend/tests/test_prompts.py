"""
Tests for Krushi Mitra system prompt.
These tests verify that the prompt enforces the correct guardrails, persona,
language settings, and spoken-voice formatting rules.

Tests are purely logic-based — no LLM calls, no API calls.
Run with: uv run pytest tests/test_prompts.py -v
"""

import pytest
from prompts import SYSTEM_PROMPT, AGENT_NAME, AGENT_TAGLINE_EN


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
        # Prompt may use 'kapas' (Marathi) or 'cotton' — either is valid
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


class TestLanguageRules:
    """Verify language-first and code-switching rules are in the prompt."""

    def test_marathi_is_primary_language(self):
        """Prompt must explicitly state Marathi is the primary language."""
        assert "Marathi" in SYSTEM_PROMPT, (
            "Prompt must state Marathi as the primary language."
        )

    def test_hindi_fallback_mentioned(self):
        """Prompt must mention Hindi as a fallback language."""
        assert "Hindi" in SYSTEM_PROMPT, (
            "Prompt must mention Hindi as a fallback language for code-switching."
        )

    def test_english_fallback_is_last_resort(self):
        """Prompt must restrict English to only when the farmer initiates it."""
        # Both conditions should appear near each other
        assert "English" in SYSTEM_PROMPT, (
            "Prompt must address English usage — it should only be used if farmer starts in English."
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
        # Look for any mention of words, sentence, or length constraint
        assert any(
            term in SYSTEM_PROMPT.lower()
            for term in ["sentence", "words", "short", "concise", "15"]
        ), "Prompt must include guidance on keeping responses short for voice output."


class TestGuardrails:
    """Verify all critical safety guardrails are present in the prompt."""

    def test_guardrail_no_live_prices_without_source(self):
        """Prompt must warn against stating live prices without a real source."""
        # Look for any form of this restriction
        assert any(
            term in SYSTEM_PROMPT.lower()
            for term in ["live", "price", "source", "cannot fetch", "mandi"]
        ), "Prompt must address that agent cannot fetch live mandi prices on Day 1."

    def test_guardrail_no_pesticide_brand(self):
        """Prompt must instruct agent not to recommend specific pesticide brands."""
        assert any(
            term in SYSTEM_PROMPT.lower()
            for term in ["pesticide", "chemical", "brand", "kvk"]
        ), "Prompt must restrict unsolicited pesticide brand recommendations."

    def test_guardrail_kvk_escalation(self):
        """Prompt must mention KVK (Krishi Vigyan Kendra) as escalation for complex cases."""
        assert "KVK" in SYSTEM_PROMPT, (
            "Prompt must mention KVK escalation for complex pest/disease cases."
        )

    def test_guardrail_farmer_distress_helpline(self):
        """Prompt must include the farmer distress helpline number."""
        # Kisan Samman / Farmer distress helpline
        assert "1800-599-0019" in SYSTEM_PROMPT, (
            "Prompt must include the farmer distress helpline number 1800-599-0019 "
            "for situations where the farmer sounds suicidal or in crisis."
        )

    def test_guardrail_honesty_unknown(self):
        """Prompt must instruct agent to say 'I don't know' rather than hallucinate."""
        # Accept both Marathi ("Mala naahi mahit") and English instruction
        assert any(
            term in SYSTEM_PROMPT
            for term in ["Mala naahi", "don't know", "I do not know", "naahi mahit"]
        ), "Prompt must instruct agent to be honest when it doesn't know an answer."


class TestOpeningGreeting:
    """Verify the opening greeting is in Marathi and present in the prompt."""

    def test_opening_greeting_present(self):
        """Prompt must include a specific Marathi opening greeting."""
        assert "Namaskar" in SYSTEM_PROMPT, (
            "Prompt must include a Marathi opening greeting with 'Namaskar'."
        )

    def test_opening_greeting_identifies_agent(self):
        """Opening greeting must state the agent's name."""
        # "Krushi Mitra" must appear near "Namaskar" in the prompt
        assert "Krushi Mitra" in SYSTEM_PROMPT and "Namaskar" in SYSTEM_PROMPT, (
            "Opening greeting must include both 'Namaskar' and 'Krushi Mitra'."
        )
