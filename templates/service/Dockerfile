FROM python:3.14-slim

ARG SERVICE_VERSION=0.1.0

LABEL org.opencontainers.image.title="SaaS Service Template"
LABEL org.opencontainers.image.version="${SERVICE_VERSION}"
LABEL org.opencontainers.image.description="Runnable starting point for an owned SaaS service"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SERVICE_HOST=0.0.0.0 \
    SERVICE_PORT=8000

WORKDIR /app

RUN useradd --create-home --uid 10001 service

COPY --chown=service:service project/ /app/project/

USER service

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)" || exit 1

CMD ["python", "-m", "project"]
