# Spec Delta: Observability and Telemetry

## Purpose
Collects real-time latency measurements across all pipeline stages and exposes health-check probes for deployment environments.

## ADDED Requirements

### Requirement: Latency Stage Tracking
The system SHALL measure and log turn turnaround metrics including VAD latency, Time to First Token (TTFT), and Time to First Audio (TTFA).

#### Scenario: End-to-end turn metric logging
- **WHEN** a user turn completes and agent audio playback begins
- **THEN** the system logs the duration of each pipeline stage in milliseconds to the structured application log

### Requirement: Health and Readiness Probes
The backend service SHALL expose an asynchronous health check probe reporting component readiness and connectivity status.

#### Scenario: Health probe query
- **WHEN** the container orchestrator queries the health endpoint
- **THEN** the probe returns HTTP 200 with pipeline readiness status
