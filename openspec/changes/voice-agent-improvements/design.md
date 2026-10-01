# Design: Voice Agent Production Improvements

## Context
See `proposal.md` for overall motivation. The system runs on LiveKit Agents with Deepgram Nova-3 STT, Groq LLaMA 3.3 70B LLM, and Murf Falcon 2 GEN2 TTS across WebRTC browser sessions and LiveKit SIP telephony trunks.

## Goals / Non-Goals

**Goals:**
- Attain sub-600ms end-to-end turnaround latency from caller pause to first synthetic audio packet.
- Ensure all numbers, currencies, and weights are articulated in spoken Marathi without markdown artifacts.
- Support multi-crop mandi pricing (Cotton, Soybean, Tur Dal) and real-time severe weather alert warnings.
- Implement zero-dependency async TTL caching for external telemetry to guarantee sub-10ms tool returns.
- Provide a standardized metrics latency tracker and container health-check probes.

**Non-Goals:**
- Custom model fine-tuning (using production foundation APIs: Deepgram Nova-3, Groq LLaMA 3.3, Murf Falcon 2).
- Full billing and carrier billing integration.

## Decisions

### 1. Dynamic Endpointing & VAD Tuning
- **Choice**: Configure `MultilingualModel` with `min_endpointing_delay=0.30s`, `max_endpointing_delay=1.5s`, and Silero VAD `activation_threshold=0.6`.
- **Rationale**: Standard default endpointing of 0.6s–0.8s introduces noticeable awkward silence. 300ms delivers an agile conversational tempo, while 1.5s max allows slower rural speakers time to pause without premature cut-offs.
- **Alternatives considered**: Fixed 0.6s endpointing (adds ~300ms latency), purely acoustic VAD without turn detector (prone to cutting mid-sentence).

### 2. Prompt-Level Phonetic Normalization
- **Choice**: Enforce audio-first Marathi spoken guidelines directly in `SYSTEM_PROMPT` in `prompts.py`.
- **Rationale**: Streaming TTS receives tokens directly from the LLM. Performing text post-processing regexes introduces pipeline buffering latency. Guiding the LLM to output spoken words (e.g. "सात हजार रुपये" instead of "₹7,000") streams zero-latency phonetic text directly into Murf Falcon 2.
- **Alternatives considered**: Downstream regex text-normalizer (delays streaming TTS chunk delivery).

### 3. Asynchronous In-Memory TTL Caching (`AsyncTTLCache`)
- **Choice**: Implement an async thread-safe TTL cache with a 30-minute expiry for weather and soil telemetry, and a persistent in-memory dictionary for mandi records.
- **Rationale**: Prevents external API rate-limiting (HTTP 429) on Open-Meteo and reduces tool execution time from 600–1200ms down to <1ms for repeated district inquiries.
- **Alternatives considered**: Redis cluster (adds unnecessary container deployment overhead).

### 4. Telemetry Latency Tracker & Healthcheck Probes
- **Choice**: Introduce `backend/src/metrics.py` with `LatencyTracker` recording TTFT, TTFA, and tool turnaround, plus an async healthcheck probe.
- **Rationale**: Gives real-time visibility into production performance across Railway/Docker deployments.

## Risks / Trade-offs

- **[Risk]** Aggressive 300ms endpointing could trigger premature turn-taking on slow speech.
  → **Mitigation**: Configured `max_endpointing_delay=1.5s` and multilingual code-switching threshold to tolerate natural mid-sentence pauses.
- **[Risk]** External Open-Meteo telemetry API temporary downtime.
  → **Mitigation**: Cached historical fallback data per Vidarbha district and graceful advisory messages.
- **[Risk]** Ephemeral SQLite database reset in stateless containers.
  → **Mitigation**: Implemented dual-mode persistence (`async_get_farmer`, `async_save_farmer`) supporting Supabase cloud DB with transparent local SQLite fallback.
