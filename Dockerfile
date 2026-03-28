# API server (run from repo root: docker build -t edgar-analyzer .)
# Stages: base -> test (CI image) -> runtime (default for compose web)
FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/

FROM base AS test

COPY requirements-dev.txt /app/requirements-dev.txt
RUN pip install --no-cache-dir -r /app/requirements-dev.txt

COPY tests/ /app/tests/
COPY pyproject.toml pytest.ini /app/

# Reference JSON used by sec_edgar.reference_data (tests and runtime)
COPY data/reference /app/data/reference

COPY docker/ci.sh /app/docker-ci.sh
RUN chmod +x /app/docker-ci.sh

WORKDIR /app
ENV PYTHONPATH=/app/src
ENV DJANGO_SETTINGS_MODULE=config.settings_test

CMD ["/app/docker-ci.sh"]

FROM base AS runtime

COPY data/reference /app/data/reference

COPY docker/entrypoint-web.sh /entrypoint-web.sh
RUN chmod +x /entrypoint-web.sh

WORKDIR /app/src

EXPOSE 8000
ENTRYPOINT ["/entrypoint-web.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
