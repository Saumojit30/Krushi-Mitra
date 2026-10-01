# Spec Delta: Latency Optimization

## Purpose
Provides low-latency voice pipeline configuration enabling sub-600ms conversational turn turnaround for agricultural callers.

## ADDED Requirements

### Requirement: Turn Detection and Dynamic Endpointing
The voice pipeline SHALL detect the end of speech within 300 milliseconds of acoustic silence to minimize conversational dead time.

#### Scenario: Speech completion turn detection
- **WHEN** the speaker stops speaking in Marathi or Hindi
- **THEN** the turn detector signals endpointing after 300 milliseconds of silence and triggers response generation

### Requirement: Preemptive Generation and Streaming Tokenization
The voice pipeline SHALL initiate LLM inference preemptively upon tentative speech endpoints and stream TTS audio chunks with single-sentence minimums.

#### Scenario: Preemptive inference audio streaming
- **WHEN** user speech endpointing is initiated
- **THEN** the LLM begins streaming response tokens and TTS synthesis delivers the first audio packet within 600 milliseconds
