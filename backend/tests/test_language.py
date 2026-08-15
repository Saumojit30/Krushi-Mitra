"""
Tests for Krushi Mitra language instructions.
Verifies the prompt handles Marathi, Hindi, and Code-mixed (Hinglish/Marathi-Hindi) scenarios.

Run with: uv run pytest tests/test_language.py -v
"""

from prompts import SYSTEM_PROMPT


class TestLanguageMirroring:
    """Verify code-mixed language instructions in the prompt."""

    def test_language_section_exists(self):
        """Prompt must contain a LANGUAGE section."""
        assert "[LANGUAGE]" in SYSTEM_PROMPT

    def test_mirror_instruction_present(self):
        """Prompt must instruct the LLM to mirror the farmer's language."""
        assert "Mirror the farmer's language perfectly" in SYSTEM_PROMPT

    def test_marathi_rule(self):
        """Prompt must have rule for pure Marathi."""
        assert "pure Marathi" in SYSTEM_PROMPT
        assert "reply in Marathi" in SYSTEM_PROMPT

    def test_hindi_rule(self):
        """Prompt must have rule for Hindi fallback."""
        assert "switch to Hindi" in SYSTEM_PROMPT

    def test_codemixed_hinglish_rule(self):
        """Prompt must handle code-mixed (Hinglish/Marathi-Hindi) explicitly."""
        assert "mix" in SYSTEM_PROMPT
        assert "same natural mix" in SYSTEM_PROMPT
        # E.g. "Bond Ali problem ahe"
        assert "Bond Ali problem ahe" in SYSTEM_PROMPT

    def test_english_restriction(self):
        """Prompt must restrict pure English unless farmer initiates."""
        assert (
            "Never use English unless the farmer initiates in English" in SYSTEM_PROMPT
        )

    def test_no_shaming_rule(self):
        """Prompt must instruct the agent not to correct the farmer's grammar or language choice."""
        assert "Never correct or shame the farmer's language choice" in SYSTEM_PROMPT
