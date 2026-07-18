# ADR-006: OPA for the Policy Engine

- **Status**: Accepted
- **Date**: 2026-07-18

## Context

AgentForge requires a foundational technology choice in this area. The decision
must support enterprise scale (10M+ executions/day), multi-tenancy, and
operational simplicity for self-hosted deployments.

## Decision

Use Open Policy Agent (Rego) for declarative policy enforcement.

## Rationale

Decoupled, auditable, declarative policies that compile to a single evaluation point.

## Alternatives Considered

Cedar (AWS-specific), custom policy DSL (maintenance).

## Consequences

The platform integrates this technology behind a stable abstraction so that
production deployments can swap managed services in while local development uses
lightweight in-process backends.
