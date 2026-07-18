# ADR-010: Redis Cluster for Caching

- **Status**: Accepted
- **Date**: 2026-07-18

## Context

AgentForge requires a foundational technology choice in this area. The decision
must support enterprise scale (10M+ executions/day), multi-tenancy, and
operational simplicity for self-hosted deployments.

## Decision

Use Redis Cluster for caching, rate limiting, and session state.

## Rationale

Sub-millisecond latency and rich data structures (token buckets, pub/sub, sorted sets).

## Alternatives Considered

Memcached (fewer features), Hazelcast (JVM-based).

## Consequences

The platform integrates this technology behind a stable abstraction so that
production deployments can swap managed services in while local development uses
lightweight in-process backends.
