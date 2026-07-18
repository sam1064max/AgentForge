# ADR-011: Hybrid Tenant Isolation

- **Status**: Accepted
- **Date**: 2026-07-18

## Context

AgentForge requires a foundational technology choice in this area. The decision
must support enterprise scale (10M+ executions/day), multi-tenancy, and
operational simplicity for self-hosted deployments.

## Decision

Use a hybrid isolation model: RLS for data, namespaces for compute, prefixes for cache.

## Rationale

Balances strict isolation with resource efficiency across 100+ tenants.

## Alternatives Considered

DB-per-tenant (costly at scale), schema-per-tenant (limited isolation).

## Consequences

The platform integrates this technology behind a stable abstraction so that
production deployments can swap managed services in while local development uses
lightweight in-process backends.
