"""
conftest.py — Pytest configuration for Krushi Mitra backend tests.

Test separation strategy:
  - Unit tests (default): pure Python, no API calls, run instantly.
    Files: test_prompts.py, test_language.py, test_logger.py
  - Integration tests: require LiveKit + Groq API keys, run against a real agent.
    Files: test_agent.py — marked with @pytest.mark.integration
    Run with: uv run pytest -m integration

Usage:
    uv run pytest                  # runs only unit tests (fast)
    uv run pytest -m integration   # runs LLM-judged integration tests (needs .env.local)
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests that require live API keys.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require live API keys (deselect with -m 'not integration')",
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --integration flag is passed."""
    if not config.getoption("--integration"):
        skip_integration = pytest.mark.skip(
            reason="Integration test — needs live API keys. Run with: uv run pytest -m integration"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
