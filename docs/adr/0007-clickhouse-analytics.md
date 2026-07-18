# ADR-007: ClickHouse for Analytics

- **Status**: Accepted
- **Date**: 2026-07-18

## Context

AgentForge requires a foundational technology choice in this area. The decision
must support enterprise scale (10M+ executions/day), multi-tenancy, and
operational simplicity for self-hosted deployments.

## Decision

Use ClickHouse for telemetry, logs, and analytics aggregation.

## Rationale

Column-oriented engine with sub-second aggregations over billions of rows and strong compression.

## Alternatives Considered

TimescaleDB (row-oriented at scale), Druid (operational complexity).

## Consequences

The platform integrates this technology behind a stable abstraction so that
production deployments can swap managed services in while local development uses
lightweight in-process backends.
