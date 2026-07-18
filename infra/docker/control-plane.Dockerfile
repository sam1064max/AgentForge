# SPDX-License-Identifier: Apache-2.0
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY services/control_plane/pyproject.toml ./services/control_plane/pyproject.toml
RUN pip install --no-cache-dir fastapi uvicorn pydantic

# Copy service source.
COPY services/control_plane ./services/control_plane
COPY sdk/agentforge/agentforge ./sdk/agentforge/agentforge

EXPOSE 8080
CMD ["uvicorn", "services.control_plane.app:app", "--host", "0.0.0.0", "--port", "8080"]
