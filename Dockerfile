# syntax=docker/dockerfile:1

# --- BUILDER STAGE ---
# Install dependencies in a separate stage so build tools don't bloat the final image
FROM python:3.13-slim-bookworm AS builder

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- DEV STAGE ---
FROM python:3.13-slim-bookworm AS dev

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code/src

COPY --from=builder /install /usr/local
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt && pip install --no-cache-dir watchdog

COPY ./src ./src

CMD ["watchmedo", "auto-restart", "--directory=./src", "--pattern=*.py", "--recursive", "--", "python", "src/main.py"]

# --- PROD STAGE ---
FROM python:3.13-slim-bookworm AS prod

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code/src

# slim-bookworm doesn't include CA certificates by default — required for HTTPS
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy only installed packages from the builder — no gcc, musl-dev, etc.
COPY --from=builder /install /usr/local
COPY ./src ./src

CMD ["python", "src/main.py"]
