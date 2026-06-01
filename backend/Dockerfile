# Base image policy: see docs/BASE_IMAGE_UPDATE_POLICY.md
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./

# Patch CVE-2026-31789: OpenSSL heap buffer overflow
# Remove once python:3.11-slim-bookworm ships with patched openssl
RUN apt-get update && apt-get upgrade -y --no-install-recommends openssl \
    && apt-get install -y --no-install-recommends \
    gcc=4:12.2.0-3 \
    libcairo2-dev=1.16.0-7 \
    pkg-config=1.8.1-1 \
    python3-dev=3.11.2-1+b1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY secuscan ./secuscan

# Non-root user
RUN groupadd --gid 1001 secuscan \
    && useradd --uid 1001 --gid secuscan --shell /usr/sbin/nologin --create-home secuscan \
    && chown -R secuscan:secuscan /app

USER secuscan

EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/api/v1/health')" || exit 1


EXPOSE 8081

CMD ["uvicorn", "secuscan.main:app", "--host", "0.0.0.0", "--port", "8081"]