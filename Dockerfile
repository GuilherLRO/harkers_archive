# Harker's Archive — run helsings_round.py (bot + scheduled transcription + dossier + Rainfields).
FROM python:3.13-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# Install dependencies (layer cache before full source copy).
COPY pyproject.toml uv.lock ./
COPY sewards_phonograph/pyproject.toml sewards_phonograph/README.md sewards_phonograph/
COPY mina_typewriter/pyproject.toml mina_typewriter/README.md mina_typewriter/
COPY van_helsings_dossier/pyproject.toml van_helsings_dossier/README.md van_helsings_dossier/
COPY rainfields_mind/agent/pyproject.toml rainfields_mind/agent/README.md rainfields_mind/agent/

RUN uv sync --all-packages --frozen --no-dev --no-install-project

COPY . .

RUN uv sync --all-packages --frozen --no-dev

CMD ["uv", "run", "python", "helsings_round.py"]
