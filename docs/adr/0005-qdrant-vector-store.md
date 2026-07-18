# ADR-005: Qdrant for Vector Storage

- **Status**: Accepted
- **Date**: 2026-07-18

## Context

AgentForge requires a foundational technology choice in this area. The decision
must support enterprise scale (10M+ executions/day), multi-tenancy, and
operational simplicity for self-hosted deployments.

## Decision

Use Qdrant as the managed vector store.

## Rationale

High-performance HNSW, rich payload filtering, multi-tenancy via collections, and sharding.

## Alternatives Considered

Weaviate (heavier ops), Pinecone (vendor lock-in).

## Consequences

The platform integrates this technology behind a stable abstraction so that
production deployments can swap managed services in while local development uses
lightweight in-process backends.
