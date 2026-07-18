"""Smoke test for Phase 3: workflow engine and scheduler."""

import asyncio
import sys

sys.path.insert(0, "sdk")

from agentforge import Agent, Tool, ModelConfig
from agentforge.models import FunctionCall, ToolCall
from agentforge.orchestration import Workflow, ToolStep, AgentStep, Scheduler
from agentforge.runtime import AgentContext


@Tool(name="square", description="Square a number")
def square(x: int) -> int:
    return x * x


@Agent(name="echo", version="1.0.0", model=ModelConfig(provider="mock", model="mock"))
class Echo:
    def __init__(self, ctx: AgentContext) -> None:
        self.ctx = ctx

    @Agent.on_message
    async def handle(self, message: str) -> str:
        return f"echo:{message}"


def main() -> None:
    # Workflow: square tool -> echo agent (input_from square step)
    wf = (
        Workflow(name="demo", version="1.0.0")
        .add(ToolStep("t1", tool="square", args={"x": 4}))
        .add(AgentStep("a1", agent="echo", input_from="t1"))
    )
    result = asyncio.run(wf.run())
    print("workflow status:", result["status"])
    print("workflow outputs:", result["outputs"])
    assert result["status"] == "completed"
    assert result["outputs"]["t1"] == 16
    assert result["outputs"]["a1"] == "echo:16"

    # Scheduler smoke: interval job runs at least once.
    import time as _t

    async def run_scheduler() -> int:
        sched = Scheduler()
        sched.add_interval(job_id="j1", agent="echo", message="tick", every_seconds=0.1)
        sched.start()
        await asyncio.sleep(0.35)
        await sched.stop()
        return sched.list_jobs()[0].runs

    runs = asyncio.run(run_scheduler())
    print("scheduler runs:", runs)
    assert runs >= 1

    print("PHASE 3 SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
