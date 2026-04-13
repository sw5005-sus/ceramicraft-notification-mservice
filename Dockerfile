FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
COPY serve.py ./

RUN uv sync --frozen --no-dev

EXPOSE 8080 50051

CMD ["uv", "run", "--no-dev", "python", "serve.py", "start"]
