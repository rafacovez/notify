# syntax=docker/dockerfile:1

FROM python:3.13-alpine AS base

WORKDIR /code

RUN apk add --no-cache gcc musl-dev libffi-dev python3-dev

COPY requirements.txt requirements-dev.txt ./

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./src ./src
COPY ./data ./data

FROM base AS dev

RUN pip install --no-cache-dir --upgrade -r requirements-dev.txt

RUN pip install watchdog

CMD ["watchmedo", "auto-restart", "--pattern=*.py", "--recursive", "--", "python", "src/main.py"]

FROM base AS prod

CMD ["python", "src/main.py"]
