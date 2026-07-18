# ADR-003: Kafka for the Event Bus

- **Status**: Accepted
- **Date**: 2026-07-18

## Context

AgentForge requires a foundational technology choice in this area. The decision
must support enterprise scale (10M+ executions/day), multi-tenancy, and
operational simplicity for self-hosted deployments.

## Decision

Use Apache Kafka as the platform event backbone.

## Rationale

Exactly-once-ish delivery, multi-consumer topics, massive throughput, and mature tooling.

## Alternatives Considered

Pulsar (smaller ecosystem), NATS (less durability guarantees).

## Consequences

The platform integrates this technology behind a stable abstraction so that
production deployments can swap managed services in while local development uses
lightweight in-process backends.
