FROM python:3.12.6-slim

RUN apt-get update

WORKDIR /Feedback-Bot/bin

COPY pyproject.toml poetry.lock* ./

RUN python -m pip install --no-cache-dir poetry==1.8.3 \
    && poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction --no-ansi \
    && rm -rf $(poetry config cache-dir)/{cache,artifacts}

COPY . .

ENTRYPOINT ["python3", "-B", "-m", "app"]
