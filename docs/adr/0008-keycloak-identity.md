# ADR-008: Keycloak for Identity

- **Status**: Accepted
- **Date**: 2026-07-18

## Context

AgentForge requires a foundational technology choice in this area. The decision
must support enterprise scale (10M+ executions/day), multi-tenancy, and
operational simplicity for self-hosted deployments.

## Decision

Use Keycloak as the identity provider.

## Rationale

OIDC/SAML federation, multi-tenancy, fine-grained AuthN, and open-source.

## Alternatives Considered

Auth0 (commercial lock-in), Zitadel (less mature at decision time).

## Consequences

The platform integrates this technology behind a stable abstraction so that
production deployments can swap managed services in while local development uses
lightweight in-process backends.
