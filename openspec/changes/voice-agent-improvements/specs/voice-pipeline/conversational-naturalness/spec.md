# Spec Delta: Conversational Naturalness

## Purpose
Ensures spoken voice interactions sound phonetically natural, respectful, and appropriately concise for rural Marathi callers.

## ADDED Requirements

### Requirement: Phonetic Spoken Normalization
The assistant SHALL render all currencies, units of measure, and numerals in spoken Marathi phonetics rather than raw symbols or abbreviations.

#### Scenario: Currency formatting in spoken response
- **WHEN** the assistant conveys an APMC mandi price such as 7500 rupees per quintal
- **THEN** the spoken transcript produces "सात हजार पाचशे रुपये प्रति क्विंटल" rather than raw symbols or English abbreviations

### Requirement: Conversational Turn Length and Recovery
The assistant SHALL restrict responses to a maximum of two spoken sentences per turn and acknowledge interruptions gracefully.

#### Scenario: Interruption barge-in recovery
- **WHEN** the caller speaks while the assistant is speaking
- **THEN** the audio output stops immediately and the assistant yields to the caller without repeating prior text
