# Spec Delta: Agricultural Data

## Purpose
Provides resilient real-time soil moisture telemetry, multi-commodity mandi pricing, and severe weather warnings with high-performance caching.

## ADDED Requirements

### Requirement: Soil Moisture and Irrigation Advisory
The system SHALL query root-zone soil moisture and ET0 evapotranspiration from the Open-Meteo Agricultural API and recommend irrigation durations.

#### Scenario: Soil moisture query with null filtering
- **WHEN** the caller inquires about irrigation or soil status for a district
- **THEN** the system filters missing sensor values, evaluates soil deficit, and returns specific watering duration in under 2 seconds

### Requirement: Multi-Commodity Mandi Pricing
The system SHALL provide APMC mandi modal, minimum, and maximum prices for cotton, soybean, and tur dal crops across Vidarbha districts.

#### Scenario: Soybean price inquiry
- **WHEN** a farmer asks for the current soybean rate in Akola APMC
- **THEN** the system fetches modal and range prices and reports them phonetically in Marathi

### Requirement: Severe Weather Alert Advisory
The system SHALL evaluate extreme precipitation, heatwave, or sudden storm risk for the caller's district and deliver immediate safety advisories.

#### Scenario: Severe storm detection
- **WHEN** meteorological data indicates wind speeds exceeding 40 km/h or unseasonal heavy rain during harvest
- **THEN** the system issues an urgent warning to protect harvested crop bolls
