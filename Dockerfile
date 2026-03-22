FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Copy and install dependencies first for better layer caching
COPY pyproject.toml uv.lock* ./
# The uv.lock might not exist yet, so we make it optional and generate it if needed
RUN uv sync --no-dev

# Copy the rest of the application code
COPY src/ ./src/
COPY protos/ ./protos/
COPY serve.py ./

# Expose the ports the service will run on
EXPOSE 8080
EXPOSE 50051

# The command to run the application
CMD ["uv", "run", "serve", "start"]
