FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
COPY serve.py ./

RUN uv sync --frozen --no-dev

EXPOSE 8080
EXPOSE 50051

CMD ["uv", "run", "python", "serve.py", "start"]
