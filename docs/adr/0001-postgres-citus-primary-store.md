# ADR-001: PostgreSQL + Citus for Primary Store

- **Status**: Accepted
- **Date**: 2026-07-18

## Context

AgentForge requires a foundational technology choice in this area. The decision
must support enterprise scale (10M+ executions/day), multi-tenancy, and
operational simplicity for self-hosted deployments.

## Decision

Use PostgreSQL 16+ with the Citus extension as the primary transactional store.

## Rationale

ACID guarantees, first-class JSONB support, Row-Level Security for multi-tenancy, and horizontal scaling via Citus sharding.

## Alternatives Considered

CockroachDB (younger ecosystem at decision time), MongoDB (no true ACID across documents).

## Consequences

The platform integrates this technology behind a stable abstraction so that
production deployments can swap managed services in while local development uses
lightweight in-process backends.
