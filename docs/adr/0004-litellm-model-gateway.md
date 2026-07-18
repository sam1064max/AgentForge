# ADR-004: LiteLLM as Model Gateway Base

- **Status**: Accepted
- **Date**: 2026-07-18

## Context

AgentForge requires a foundational technology choice in this area. The decision
must support enterprise scale (10M+ executions/day), multi-tenancy, and
operational simplicity for self-hosted deployments.

## Decision

Build the Model Gateway on top of LiteLLM.

## Rationale

100+ provider support behind one API, active community, and built-in fallbacks.

## Alternatives Considered

Fully custom provider adapters (heavy maintenance burden).

## Consequences

The platform integrates this technology behind a stable abstraction so that
production deployments can swap managed services in while local development uses
lightweight in-process backends.
