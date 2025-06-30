FROM python:3.12-slim

# Install uv (Python dependency manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Node.js and pnpm
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g pnpm && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN uv sync

WORKDIR /app/ui
RUN pnpm install

WORKDIR /app

RUN pip install --no-cache-dir sh

CMD ["sh", "-c", "uv run ./main.py & cd ui && pnpm dev"]
