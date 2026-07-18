"""Scheduler.

Triggers agent runs on a schedule (interval or cron-like expression). The local
scheduler runs in-process via ``asyncio`` and supports enable/disable, one-shot,
and tagged jobs. Production deployments use the Scheduler service (durable,
multi-node). See `docs/architecture/03-*.md`.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from agentforge.exceptions import ValidationError
from agentforge.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ScheduledJob:
    job_id: str
    agent: str
    message: str
    every_seconds: float | None = None
    cron: str | None = None
    enabled: bool = True
    last_run: float = 0.0
    next_run: float = 0.0
    runs: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def describe(self) -> str:
        if self.cron:
            return f"cron:{self.cron}"
        return f"every {self.every_seconds}s"


class Scheduler:
    """In-process scheduler for agent triggers."""

    def __init__(self, *, tenant_id: str | None = None) -> None:
        self.tenant_id = tenant_id
        self._jobs: dict[str, ScheduledJob] = {}
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    # ── Registration ─────────────────────────────────────────
    def add_interval(self, *, job_id: str, agent: str, message: str,
                     every_seconds: float, enabled: bool = True) -> ScheduledJob:
        if every_seconds <= 0:
            raise ValidationError("every_seconds must be positive")
        job = ScheduledJob(job_id=job_id, agent=agent, message=message,
                           every_seconds=every_seconds, enabled=enabled,
                           next_run=time.monotonic() + every_seconds)
        self._jobs[job_id] = job
        return job

    def add_cron(self, *, job_id: str, agent: str, message: str,
                 cron: str, enabled: bool = True) -> ScheduledJob:
        self._validate_cron(cron)
        job = ScheduledJob(job_id=job_id, agent=agent, message=message,
                           cron=cron, enabled=enabled,
                           next_run=time.monotonic())
        self._jobs[job_id] = job
        return job

    def enable(self, job_id: str) -> None:
        self._jobs[job_id].enabled = True

    def disable(self, job_id: str) -> None:
        self._jobs[job_id].enabled = False

    def remove(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)

    def list_jobs(self) -> list[ScheduledJob]:
        return list(self._jobs.values())

    # ── Lifecycle ────────────────────────────────────────────
    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _loop(self) -> None:
        from agentforge.registry import registry
        from agentforge.runtime.engine import execute_agent

        while not self._stop.is_set():
            now = time.monotonic()
            for job in list(self._jobs.values()):
                if not job.enabled or now < job.next_run:
                    continue
                job.last_run = now
                job.runs += 1
                job.next_run = now + (job.every_seconds or _cron_to_delay(job.cron))
                try:
                    definition = registry.get_agent(job.agent)
                    result = await execute_agent(definition, message=job.message,
                                                 tenant_id=self.tenant_id)
                    logger.info("scheduled run", extra={"attributes": {
                        "job": job.job_id, "status": result.status}})
                except Exception as exc:  # noqa: BLE001
                    logger.error("scheduled run failed", extra={"attributes": {
                        "job": job.job_id, "error": str(exc)}})
            # Sleep until the soonest due job (or 1s if none pending).
            delay = 1.0
            for job in self._jobs.values():
                if job.enabled:
                    due = job.next_run - time.monotonic()
                    if due > 0:
                        delay = min(delay, due)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass

    # ── Cron validation (5-field, numeric/simple) ───────────
    @staticmethod
    def _validate_cron(cron: str) -> None:
        parts = cron.split()
        if len(parts) != 5:
            raise ValidationError("cron must have 5 fields: m h dom mon dow")
        field_re = re.compile(r"^(\*|\d+(-\d+)?(/,?\d+)*)$")
        for p in parts:
            if not field_re.match(p):
                raise ValidationError(f"invalid cron field: '{p}'")


def _cron_to_delay(cron: str) -> float:
    """Best-effort next-run delay (seconds) for a 5-field cron.

    This is a simplified scheduler: it computes the delay to the next minute
    boundary where the minute field matches. Full cron precision is provided by
    the production Scheduler service.
    """
    minute_field = cron.split()[0]
    now = time.localtime()
    if minute_field == "*":
        return 60.0
    minutes = [int(m) for m in minute_field.replace("*/", "").split(",") if m.isdigit()] or [now.tm_min]
    target = min(minutes, key=lambda m: (m - now.tm_min) % 60)
    delay_min = (target - now.tm_min) % 60 or 60
    return float(delay_min * 60)
