# ADR-009: LangGraph for Agent State Machines

- **Status**: Accepted
- **Date**: 2026-07-18

## Context

AgentForge requires a foundational technology choice in this area. The decision
must support enterprise scale (10M+ executions/day), multi-tenancy, and
operational simplicity for self-hosted deployments.

## Decision

Use LangGraph as the agent state-machine runtime base.

## Rationale

Python-native, flexible graph execution, and a growing ecosystem.

## Alternatives Considered

AutoGen (Microsoft-centric), fully custom runtime (high effort).

## Consequences

The platform integrates this technology behind a stable abstraction so that
production deployments can swap managed services in while local development uses
lightweight in-process backends.
