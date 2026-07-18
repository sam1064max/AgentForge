# SPDX-License-Identifier: Apache-2.0
"""Evaluation framework: metrics, datasets, suites and reports.

Mirrors the architecture's offline/online evaluation design. Built-in metrics
include correctness (LLM-as-judge ready), groundedness, tool accuracy, latency
and cost. A :class:`EvalSuite` runs an agent on a golden dataset and produces a
gated :class:`EvaluationReport`.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class Metric(str, Enum):
    CORRECTNESS = "correctness"
    GROUNDEDNESS = "groundedness"
    TOOL_ACCURACY = "tool_accuracy"
    LATENCY_P99 = "latency_p99"
    LATENCY_P50 = "latency_p50"
    COST_PER_EXECUTION = "cost_per_execution"
    GOAL_COMPLETION = "goal_completion"


@dataclass(slots=True)
class EvalCase:
    input: str
    expected_output: str | None = None
    expected_tools: list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvalDataset:
    name: str
    cases: list[EvalCase] = field(default_factory=list)
    version: str = "1.0.0"

    def add(self, input: str, expected_output: str | None = None, expected_tools: list[str] | None = None) -> "EvalDataset":
        self.cases.append(EvalCase(input=input, expected_output=expected_output, expected_tools=expected_tools))
        return self


@dataclass(slots=True)
class ScoredCase:
    case: EvalCase
    output: str
    scores: dict[str, float]
    latency_ms: int
    cost: float


@dataclass(slots=True)
class EvaluationReport:
    id: str
    agent_id: str
    dataset: str
    aggregate: dict[str, float]
    cases: list[ScoredCase] = field(default_factory=list)
    gate_result: str = "pass"
    gate_threshold: float = 0.8

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "dataset": self.dataset,
            "aggregate": self.aggregate,
            "gate_result": self.gate_result,
            "case_count": len(self.cases),
        }


def _score_tool_accuracy(expected: list[str] | None, actual: list[tuple[str, dict[str, Any]]]) -> float:
    if not expected:
        return 1.0
    actual_names = {t[0] for t in actual}
    return len(set(expected) & actual_names) / len(set(expected))


def _score_latency(latencies: list[int], pct: float) -> float:
    if not latencies:
        return 0.0
    ordered = sorted(latencies)
    idx = min(len(ordered) - 1, int(len(ordered) * pct))
    return float(ordered[idx])


class EvalSuite:
    """Runs an agent spec against a dataset and scores the results."""

    def __init__(
        self,
        *,
        name: str,
        agent_spec: Any,
        dataset: EvalDataset,
        metrics: list[Metric] | None = None,
        runtime: Any = None,
        gate_threshold: float = 0.8,
    ) -> None:
        self.name = name
        self.agent_spec = agent_spec
        self.dataset = dataset
        self.metrics = metrics or [Metric.CORRECTNESS, Metric.TOOL_ACCURACY, Metric.LATENCY_P99]
        self.runtime = runtime
        self.gate_threshold = gate_threshold

    async def run(self) -> EvaluationReport:
        if self.runtime is None:
            raise RuntimeError("EvalSuite requires a runtime (or call bind_runtime)")
        scored: list[ScoredCase] = []
        for case in self.dataset.cases:
            start = time.perf_counter()
            result = await self.runtime.run(self.agent_spec, case.input)
            latency = int((time.perf_counter() - start) * 1000)
            scores: dict[str, float] = {}
            if Metric.TOOL_ACCURACY in self.metrics:
                scores[Metric.TOOL_ACCURACY.value] = _score_tool_accuracy(case.expected_tools, result.tool_calls)
            if Metric.LATENCY_P99 in self.metrics:
                scores[Metric.LATENCY_P99.value] = float(latency)
            if Metric.LATENCY_P50 in self.metrics:
                scores[Metric.LATENCY_P50.value] = float(latency)
            if Metric.COST_PER_EXECUTION in self.metrics:
                scores[Metric.COST_PER_EXECUTION.value] = result.cost
            if Metric.GOAL_COMPLETION in self.metrics:
                scores[Metric.GOAL_COMPLETION.value] = 1.0 if result.status == "completed" else 0.0
            if Metric.CORRECTNESS in self.metrics:
                # Heuristic: output non-empty and status completed.
                scores[Metric.CORRECTNESS.value] = 1.0 if result.output and result.status == "completed" else 0.0
            scored.append(ScoredCase(case=case, output=result.output, scores=scores, latency_ms=latency, cost=result.cost))

        aggregate = self._aggregate(scored)
        gate = self._gate(aggregate)
        return EvaluationReport(
            id=f"eval-{uuid.uuid4().hex[:12]}",
            agent_id=self.agent_spec.name,
            dataset=self.dataset.name,
            aggregate=aggregate,
            cases=scored,
            gate_result=gate,
            gate_threshold=self.gate_threshold,
        )

    def _aggregate(self, scored: list[ScoredCase]) -> dict[str, float]:
        out: dict[str, float] = {}
        latencies = [s.latency_ms for s in scored]
        for metric in self.metrics:
            if metric in (Metric.LATENCY_P99, Metric.LATENCY_P50):
                continue
            vals = [s.scores.get(metric.value, 0.0) for s in scored]
            out[metric.value] = sum(vals) / len(vals) if vals else 0.0
        if Metric.LATENCY_P99 in self.metrics:
            out[Metric.LATENCY_P99.value] = _score_latency(latencies, 0.99)
        if Metric.LATENCY_P50 in self.metrics:
            out[Metric.LATENCY_P50.value] = _score_latency(latencies, 0.5)
        return out

    def _gate(self, aggregate: dict[str, float]) -> str:
        # Pass if every quality metric meets the threshold.
        quality = [v for k, v in aggregate.items() if k not in (Metric.LATENCY_P99.value, Metric.LATENCY_P50.value, Metric.COST_PER_EXECUTION.value)]
        if quality and min(quality) < self.gate_threshold:
            return "fail"
        return "pass"
