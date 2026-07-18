# SPDX-License-Identifier: Apache-2.0
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY sdk/agentforge/pyproject.toml ./sdk/agentforge/pyproject.toml
RUN pip install --no-cache-dir pydantic httpx

COPY sdk/agentforge/agentforge ./sdk/agentforge/agentforge

# The SDK is imported by agents at runtime; expose it on the path.
ENV PYTHONPATH=/app
CMD ["python", "-c", "import agentforge; print('AgentForge SDK', agentforge.__version__)"]
