# ADR-002: Temporal for Durable Workflows

- **Status**: Accepted
- **Date**: 2026-07-18

## Context

AgentForge requires a foundational technology choice in this area. The decision
must support enterprise scale (10M+ executions/day), multi-tenancy, and
operational simplicity for self-hosted deployments.

## Decision

Use Temporal as the workflow engine for durable, long-running agent orchestration.

## Rationale

Battle-tested exactly-once semantics, built-in retries, sagas, and replayable state — essential for enterprise SLAs.

## Alternatives Considered

Custom engine (high risk), Cadence (smaller community).

## Consequences

The platform integrates this technology behind a stable abstraction so that
production deployments can swap managed services in while local development uses
lightweight in-process backends.
