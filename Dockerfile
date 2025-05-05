# FROM python:3.13-alpine

# WORKDIR /code

# COPY ./requirements.txt /code/requirements.txt

# RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# COPY ./app /code/app

# CMD ["python", "./app/main.py"]

# --- DEVELOPMENT ---
# DELETE AND UNCOMMENT ABOVE BEFORE PUSHING

FROM python:3.13-alpine

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

CMD ["python", "-m", "watchdog", "app/main.py"]

# docker build -t notify-bot .

# docker run --rm -it \
#   -v $(pwd)/app:/code/app \
#   -p 8080:80 \
#   --env-file app/config/.env.local \
#   --name notify-bot \
#   notify-bot \
#   watchmedo auto-restart --pattern="*.py" --recursive -- python ./app/main.py