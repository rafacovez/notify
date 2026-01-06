# syntax=docker/dockerfile:1
FROM python:3.13-alpine AS base

WORKDIR /code

# 1. Performance and Logging optimizations
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code/src

# 2. Install build dependencies, install requirements, then REMOVE dependencies
# This keeps the image small
COPY requirements.txt requirements-dev.txt ./
RUN apk add --no-cache --virtual .build-deps gcc musl-dev libffi-dev python3-dev \
    && pip install --no-cache-dir --upgrade -r requirements.txt \
    && apk del .build-deps

COPY ./src ./src

# --- DEV STAGE ---
FROM base AS dev
RUN pip install --no-cache-dir --upgrade -r requirements-dev.txt
RUN pip install watchdog
# Added --directory=src so it specifically watches your code
CMD ["watchmedo", "auto-restart", "--directory=./src", "--pattern=*.py", "--recursive", "--", "python", "src/main.py"]

# --- PROD STAGE ---
FROM base AS prod
# Create data dir here so it exists even if volume mount fails
RUN mkdir -p /code/data
CMD ["python", "src/main.py"]