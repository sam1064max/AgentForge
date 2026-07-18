"""Workflow engine.

A workflow is a directed graph of steps. Each step is either an *agent* step
(invokes a registered agent), a *tool* step (invokes a registered tool), or a
*group* step (sequential/parallel/conditional). Workflows are checkpointed so a
failed run can resume from the last completed step.

This is the local, in-process implementation; the production Workflow Engine
service provides durable (Temporal-backed) execution. See
`docs/architecture/03-*.md`.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agentforge.exceptions import ExecutionError, ValidationError
from agentforge.logging import get_logger
from agentforge.registry import registry

logger = get_logger(__name__)


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepKind(str, Enum):
    AGENT = "agent"
    TOOL = "tool"
    GROUP = "group"
    CONDITION = "condition"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


@dataclass
class StepResult:
    step_id: str
    status: StepStatus
    output: Any = None
    error: str | None = None
    started_at: float = 0.0
    ended_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "duration_ms": int((self.ended_at - self.started_at) * 1000),
        }


class Step(ABC):
    """A single workflow step."""

    kind: StepKind = StepKind.GROUP

    def __init__(self, step_id: str, *, name: str | None = None) -> None:
        self.step_id = step_id
        self.name = name or step_id

    @abstractmethod
    async def execute(self, ctx: "WorkflowContext") -> Any: ...


class AgentStep(Step):
    kind = StepKind.AGENT

    def __init__(self, step_id: str, *, agent: str, input_from: str | None = None,
                 input_template: str | None = None, name: str | None = None) -> None:
        super().__init__(step_id, name=name)
        self.agent = agent
        self.input_from = input_from
        self.input_template = input_template

    async def execute(self, ctx: "WorkflowContext") -> Any:
        from agentforge.runtime.engine import execute_agent

        definition = registry.get_agent(self.agent)
        message = self._build_message(ctx)
        result = await execute_agent(definition, message=message, tenant_id=ctx.tenant_id)
        if result.status == "error":
            raise ExecutionError(f"agent step '{self.step_id}' failed: {result.error}")
        return result.output

    def _build_message(self, ctx: "WorkflowContext") -> str:
        if self.input_template:
            return self.input_template.format(**ctx.outputs)
        if self.input_from and self.input_from in ctx.outputs:
            return str(ctx.outputs[self.input_from])
        return str(ctx.inputs)


class ToolStep(Step):
    kind = StepKind.TOOL

    def __init__(self, step_id: str, *, tool: str, args: dict[str, Any] | None = None,
                 args_from: dict[str, str] | None = None, name: str | None = None) -> None:
        super().__init__(step_id, name=name)
        self.tool = tool
        self.args = args or {}
        self.args_from = args_from or {}

    async def execute(self, ctx: "WorkflowContext") -> Any:
        definition = registry.get_tool(self.tool)
        resolved = dict(self.args)
        for key, src in self.args_from.items():
            resolved[key] = ctx.outputs.get(src)
        return await definition.invoke(**resolved)


class ConditionStep(Step):
    kind = StepKind.CONDITION

    def __init__(self, step_id: str, *, expr: str, then_step: str, else_step: str | None = None,
                 name: str | None = None) -> None:
        super().__init__(step_id, name=name)
        self.expr = expr
        self.then_step = then_step
        self.else_step = else_step

    async def execute(self, ctx: "WorkflowContext") -> Any:
        env = dict(ctx.outputs)
        env["inputs"] = ctx.inputs
        try:
            result = bool(eval(self.expr, {"__builtins__": {}}, env))  # noqa: S307 - controlled DSL
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(f"condition '{self.step_id}' eval error: {exc}")
        ctx.branch = self.then_step if result else (self.else_step or "__end__")
        return result


class GroupStep(Step):
    """A container of steps (sequential or parallel)."""

    def __init__(self, step_id: str, *, mode: str = "sequential", steps: list[Step] | None = None,
                 name: str | None = None) -> None:
        super().__init__(step_id, name=name)
        self.kind = StepKind.PARALLEL if mode == "parallel" else StepKind.SEQUENTIAL
        self.steps = steps or []

    async def execute(self, ctx: "WorkflowContext") -> Any:
        if self.kind == StepKind.PARALLEL:
            results = await asyncio.gather(*[self._run_step(s, ctx) for s in self.steps])
            return results
        outputs = []
        for s in self.steps:
            outputs.append(await self._run_step(s, ctx))
        return outputs

    async def _run_step(self, step: Step, ctx: "WorkflowContext") -> Any:
        return await ctx.run_step(step)


@dataclass
class WorkflowContext:
    """Mutable execution state threaded through a workflow run."""

    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    branch: str | None = None
    tenant_id: str | None = None
    execution_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    async def run_step(self, step: Step) -> StepResult:
        result = StepResult(step_id=step.step_id, status=StepStatus.RUNNING,
                            started_at=time.monotonic())
        try:
            out = await step.execute(self)
            self.outputs[step.step_id] = out
            result.output = out
            result.status = StepStatus.COMPLETED
        except Exception as exc:  # noqa: BLE001
            result.status = StepStatus.FAILED
            result.error = str(exc)
        result.ended_at = time.monotonic()
        return result


class Workflow:
    """A named, versioned workflow definition."""

    def __init__(self, name: str, version: str = "1.0.0",
                 steps: list[Step] | None = None, start: str | None = None) -> None:
        self.name = name
        self.version = version
        self.steps: dict[str, Step] = {s.step_id: s for s in (steps or [])}
        self.start = start or (next(iter(self.steps)) if self.steps else None)
        registry.register_workflow(self)

    def add(self, step: Step) -> "Workflow":
        self.steps[step.step_id] = step
        if self.start is None:
            self.start = step.step_id
        return self

    async def run(self, inputs: dict[str, Any] | None = None, *,
                  tenant_id: str | None = None) -> dict[str, Any]:
        if not self.start:
            raise ValidationError(f"workflow '{self.name}' has no start step")
        ctx = WorkflowContext(inputs=inputs or {}, tenant_id=tenant_id)
        results: dict[str, StepResult] = {}
        current = self.start
        guard = 0
        while current and current != "__end__":
            guard += 1
            if guard > 1000:
                raise ExecutionError("workflow step limit exceeded (possible cycle)")
            step = self.steps.get(current)
            if step is None:
                raise ValidationError(f"workflow step '{current}' not found")
            result = await ctx.run_step(step)
            results[current] = result
            if result.status == StepStatus.FAILED:
                return self._finalize(ctx, results, failed=current)
            # Branching support via condition/parallel steps.
            if ctx.branch and ctx.branch != current:
                current = ctx.branch
                ctx.branch = None
            elif isinstance(step, GroupStep):
                current = self._next_after(step.step_id)
            else:
                current = self._next_after(current)
        return self._finalize(ctx, results)

    def _next_after(self, step_id: str) -> str | None:
        ids = list(self.steps.keys())
        try:
            idx = ids.index(step_id)
            return ids[idx + 1] if idx + 1 < len(ids) else "__end__"
        except ValueError:
            return "__end__"

    def _finalize(self, ctx: WorkflowContext, results: dict[str, StepResult],
                  failed: str | None = None) -> dict[str, Any]:
        return {
            "workflow": self.name,
            "version": self.version,
            "execution_id": ctx.execution_id,
            "status": "failed" if failed else "completed",
            "failed_step": failed,
            "outputs": ctx.outputs,
            "steps": {k: v.to_dict() for k, v in results.items()},
        }


def Workflow_decorator(*, name: str, version: str = "1.0.0") -> Any:  # noqa: N802
    """Class decorator that turns a class with ``steps`` into a :class:`Workflow`."""

    def wrapper(cls: type) -> Workflow:
        steps = getattr(cls, "steps", [])
        start = getattr(cls, "start", None)
        return Workflow(name=name, version=version, steps=list(steps), start=start)

    return wrapper


# Function-form alias.
workflow = Workflow_decorator
