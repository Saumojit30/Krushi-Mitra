# Krushi Mitra — Backend Voice AI Service

The Python backend for **Krushi Mitra** (कृषी मित्र), a production-grade, ultra-low-latency multilingual Voice AI advisory service for cotton and cash-crop farmers in the Vidarbha region of Maharashtra, India.

Built on the [LiveKit Agents SDK](https://docs.livekit.io/agents), it connects Murf Falcon 2 GEN2 streaming Marathi TTS, Deepgram Nova-3 multilingual STT, and fast LLM inference (Groq / Google Gemini 3 series) into a full-duplex conversational voice pipeline.

---

## Architecture & Voice Pipeline

```
[Farmer Speaks] ──► [LiveKit WebRTC / SIP] ──► [Deepgram Nova-3 STT]
                                                       │ (Marathi / Hindi text)
                                                       ▼
[Farmer Hears]  ◄── [Murf Falcon 2 GEN2 TTS] ◄── [Groq / Gemini 3 LLM]
                     (mr-IN-shilpa voice)              │
                                                       ├──► [Open-Meteo Weather API]
                                                       ├──► [APMC Mandi Price Dataset]
                                                       ├──► [CIB Pest Advisory RAG]
                                                       └──► [Supabase / SQLite Memory]
```

### Key Components:
- **Audio Transport:** LiveKit Agents SFU for WebRTC browser calls and carrier SIP trunks (`BVCTelephony` noise suppression for 8kHz phone lines).
- **Speech-to-Text (STT):** Deepgram Nova-3 (`model="nova-3", language="multi"`) with optional OpenAI Whisper fallback (`whisper-1`) for regional Varhadi dialect accuracy.
- **Large Language Model (LLM):** Dynamic provider selection supporting **Groq** (`openai/gpt-oss-20b`) and **Google Gemini 3 series** (`gemini-3.5-flash-lite` or `gemini-3.5-flash`).
- **Text-to-Speech (TTS):** Murf Falcon 2 GEN2 (`voice="mr-IN-shilpa"`, style="Conversational", single-sentence chunking `min_sentence_len=1`).
- **Turn Detection:** Silero VAD + LiveKit Multilingual Turn Detector with 300ms endpointing delay and preemptive generation.

---

## Setup & Local Development

### 1. Install Dependencies

Ensure Python 3.10+ and [`uv`](https://docs.astral.sh/uv/) are installed:

```bash
cd backend
uv sync
```

### 2. Configure Environment Variables

```bash
cp .env.example .env.local
```

Fill in your API keys in `.env.local`:

| Variable | Description | Where to Get |
| :--- | :--- | :--- |
| `LIVEKIT_URL` | LiveKit Cloud WebSocket URL | [cloud.livekit.io](https://cloud.livekit.io/) |
| `LIVEKIT_API_KEY` | LiveKit Project API Key | [cloud.livekit.io](https://cloud.livekit.io/) |
| `LIVEKIT_API_SECRET` | LiveKit Project API Secret | [cloud.livekit.io](https://cloud.livekit.io/) |
| `MURF_API_KEY` | Murf Falcon 2 TTS API Key | [murf.ai/api/dashboard](https://murf.ai/api/dashboard) |
| `MURF_VOICE_ID` | Marathi voice ID (default: `mr-IN-shilpa`) | [murf.ai/api/docs](https://murf.ai/api/docs) |
| `DEEPGRAM_API_KEY` | Deepgram STT API Key | [console.deepgram.com](https://console.deepgram.com/) |
| `STT_PROVIDER` | `deepgram` (default) or `openai` (Whisper) | Built-in |
| `LLM_PROVIDER` | `groq` or `gemini` (auto-detected if unset) | Built-in |
| `GROQ_API_KEY` | Groq Cloud API Key | [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | Active Groq model (`openai/gpt-oss-20b`) | [console.groq.com/docs/models](https://console.groq.com/docs/models) |
| `GOOGLE_API_KEY` | Gemini API Key & RAG Embeddings | [aistudio.google.com](https://aistudio.google.com) |
| `GEMINI_MODEL` | Gemini 3 model (`gemini-3.5-flash-lite`) | [aistudio.google.com](https://aistudio.google.com) |
| `SUPABASE_URL` | *(Optional)* Supabase PostgreSQL URL | [supabase.com](https://supabase.com) |
| `SUPABASE_KEY` | *(Optional)* Supabase Service Key | [supabase.com](https://supabase.com) |

### 3. Download Model Weights (First Time Only)

```bash
uv run python src/agent.py download-files
```

This pre-loads Silero VAD and LiveKit turn detection models.

### 4. Run the Agent

```bash
# Development mode with auto-reload
uv run python src/agent.py dev

# Terminal console testing (no browser required)
uv run python src/agent.py console

# Production worker
uv run python src/agent.py start
```

---

## Multi-Agent Domain Specialization

All agent prompts and specialized roles live in [`src/prompts.py`](src/prompts.py) and [`src/agent.py`](src/agent.py):

1. **Krushi Mitra (Triage Generalist)**: Initial caller greeting, returning farmer profile recognition, weather forecasts, and APMC mandi rates.
2. **Cotton Pest Specialist (`CottonPestSpecialist`)**: Integrated Pest Management (IPM), pheromone traps, and CIB-verified government remedy lookup (`get_verified_pest_remedy`).
3. **Cotton Market Specialist (`CottonMarketSpecialist`)**: Cotton Corporation of India (CCI) center selling procedures, 7/12 land records, Aadhaar/bank documents, and moisture discount bands.

---

## Available Tools

The agent uses autonomous function-calling tools:

- `get_farmer_profile` / `save_farmer_profile`: Reads and writes farmer profiles with explicit verbal consent.
- `get_last_call_summary`: Retrieves the previous conversation context for returning callers.
- `get_weather_forecast`: Queries real-time 3-day precipitation probability and temperatures from Open-Meteo.
- `get_cotton_mandi_prices`: Retrieves APMC cotton rates (Yavatmal, Amravati, Akola, Wardha) with MSP benchmarks.
- `get_verified_pest_remedy`: RAG query matching pest symptoms against official CIB agricultural advisories.
- `create_escalation`: Generates an escalation ticket to a human KVK agricultural officer.
- `handoff_to_pest_specialist` / `handoff_to_market_specialist` / `handoff_to_triage`: Seamless domain handoffs.

---

## Telephony Support (Inbound & Outbound)

Located in [`src/telephony/`](src/telephony/):

- **Inbound Agent ([`inbound/agent.py`](src/telephony/inbound/agent.py))**: Answers incoming phone calls from Indian telephone numbers via LiveKit SIP dispatch rules.
- **Outbound Agent ([`outbound/agent.py`](src/telephony/outbound/agent.py))**: Automated advisory and alert dialer.

```bash
# Start inbound phone listener
uv run python src/telephony/inbound/agent.py dev

# Place an outbound test call
uv run python src/telephony/outbound/dial.py --to +91XXXXXXXXXX
```

---

## Testing & Quality Assurance

```bash
# Run unit and performance tests
uv run pytest tests/test_performance.py -v

# Run linting and formatting
uv run ruff check .
uv run ruff format --check .
```

---

## License

MIT — see [LICENSE](../LICENSE).
