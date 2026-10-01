# Proposal: Voice Agent Production Improvements

## Why
Krushi Mitra serves cotton and rural crop farmers who interact via phone (SIP telephony) and web browsers. Delivering a natural, trustworthy conversational experience in Marathi requires sub-600ms response latency, phonetically natural spoken phrasing for currencies and quantities, resilient real-time farm data tools, and enterprise-grade deployment telemetry. This proposal addresses end-to-end latency, conversational flow, caching, and observability to ready the system for high-concurrency production deployment.

## What Changes
- **Latency Engine**: Optimize Silero VAD activation thresholds and set dynamic endpointing delay to 300ms; tune Murf Falcon 2 GEN2 streaming sentence tokenizer with `min_sentence_len=1` and token buffer pre-warming to achieve <600ms Time-to-First-Audio.
- **Conversational Naturalness**: Add phonetic conversion of prices, numbers, and weights into natural spoken Marathi; enforce strict 1-2 sentence brevity per turn; integrate conversational backchanneling and interruption (barge-in) recovery guidelines.
- **Agricultural Data Ecosystem**: Add an asynchronous in-memory TTL cache for external agricultural telemetry (Open-Meteo Soil and Weather) to avoid API rate limits and achieve <10ms tool returns; extend mandi price tool to support multiple Vidarbha crops (Cotton, Soybean, Tur Dal); add severe weather alert detection.
- **Deployment Hardening & Observability**: Add a dedicated metrics and latency tracking module (`metrics.py`), a `/healthz` health-check service, and resilient dual-backend database persistence (Supabase PostgreSQL with automatic SQLite local fallback).

## Capabilities

### New Capabilities
- `voice-pipeline/latency-optimization`: Voice activity detection threshold tuning, dynamic endpointing delay, and streaming sentence tokenization for sub-600ms voice turns.
- `voice-pipeline/conversational-naturalness`: Audio-first phonetic formatting in Marathi, natural conversational fillers, barge-in recovery, and short conversational cadence.
- `advisory/agricultural-data`: Live soil moisture, multi-crop mandi pricing, severe weather alert detection, and resilient TTL caching.
- `observability/telemetry`: Latency tracking metrics (TTFT, TTFA, VAD, tools) and container health-check probes.

### Modified Capabilities
*(None - first OpenSpec baseline)*

## Impact
- **Backend Code**: Updates to `backend/src/agent.py`, `backend/src/prompts.py`, `backend/src/database.py`, `backend/src/telephony/inbound/agent.py`, `backend/src/telephony/outbound/agent.py`, and new `backend/src/metrics.py`.
- **APIs**: Integration with Open-Meteo Agricultural API, Weather API, Agmarknet mandi cache, and optional Supabase REST API.
- **Dependencies**: No external binary dependencies required; pure Python async primitives and LiveKit Agents framework.
