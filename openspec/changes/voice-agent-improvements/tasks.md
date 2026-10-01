# Tasks: Voice Agent Production Improvements

## 1. Pipeline Latency Optimization

- [x] 1.1 Update `backend/src/agent.py` and telephony agents with `min_endpointing_delay=0.30` and Silero VAD threshold 0.6 to minimize dead time. Verify with unit tests.
- [x] 1.2 Configure Murf Falcon 2 TTS with `min_sentence_len=1` and streaming sentence tokenizer for immediate first chunk audio playback. Verify TTS initialization in tests.

## 2. Spoken Conversational Naturalness

- [x] 2.1 Enhance `backend/src/prompts.py` with audio-first phonetic normalization for Marathi prices, weights, and numerals (no symbols/abbreviations). Verify prompt formatting via unit tests.
- [x] 2.2 Add conversational backchanneling markers ("होय", "समजलं", "एक मिनिट तपासतो") and interruption recovery instructions to system prompt. Verify prompt content with unit tests.

## 3. Real Data Ecosystem and Caching

- [x] 3.1 Implement asynchronous in-memory TTL cache (`AsyncTTLCache`) for Open-Meteo Soil and Weather API queries. Verify caching behavior with unit tests.
- [x] 3.2 Extend mandi price tool to support multiple Vidarbha crops (Cotton, Soybean, Tur Dal) across `src/agent.py` and telephony agents. Verify multi-crop queries with unit tests.
- [x] 3.3 Implement severe weather alerts advisory tool (`get_weather_alerts`) checking wind speed, unseasonal rainfall, and heat conditions. Verify tool execution in `test_tools.py`.

## 4. Telemetry and Observability Hardening

- [x] 4.1 Create `backend/src/metrics.py` with `LatencyTracker` recording TTFT, TTFA, and tool turnaround, plus an async health check probe. Verify metrics logging in unit tests.
- [x] 4.2 Verify database persistence layer in `backend/src/database.py` with seamless Supabase cloud DB connectivity and local SQLite fallback. Verify async database tests pass.

## 5. End-to-End Verification and OpenSpec Validation

- [x] 5.1 Run full test suite with `uv run pytest -m "not integration"` and verify all tests pass.
- [x] 5.2 Run lint and format checks with `uv run ruff check .` and `uv run ruff format --check .`.
- [x] 5.3 Validate OpenSpec change proposal with `openspec validate voice-agent-improvements`.
