# ADR-012: Event-Driven with CQRS

- **Status**: Accepted
- **Date**: 2026-07-18

## Context

AgentForge requires a foundational technology choice in this area. The decision
must support enterprise scale (10M+ executions/day), multi-tenancy, and
operational simplicity for self-hosted deployments.

## Decision

Adopt event-driven architecture with CQRS for read/write separation.

## Rationale

Decoupled services, scalable reads, and a natural audit trail via the event log.

## Alternatives Considered

Synchronous request/response (tight coupling), pure event sourcing (operational complexity).

## Consequences

The platform integrates this technology behind a stable abstraction so that
production deployments can swap managed services in while local development uses
lightweight in-process backends.
