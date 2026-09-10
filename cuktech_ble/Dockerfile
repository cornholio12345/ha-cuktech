FROM python:3.11.13-slim-bookworm

# Audited upstream snapshot: kairui1108/cuktech-ble-server v1.1.0
# Commit: 111f57e4b3857774b4ef24ad8bfac8addb9b8ee1
ENV CUKTECH_CONFIG_PATH=/data/config.yaml \
    CUKTECH_HISTORY_DB_PATH=/data/port_history.db \
    CUKTECH_SERVER_PORT=8199 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends bluez dbus ca-certificates curl tar gzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN curl -fsSL \
      https://github.com/kairui1108/cuktech-ble-server/archive/111f57e4b3857774b4ef24ad8bfac8addb9b8ee1.tar.gz \
      -o /tmp/cuktech.tar.gz \
    && tar -xzf /tmp/cuktech.tar.gz --strip-components=1 -C /app \
    && rm /tmp/cuktech.tar.gz \
    && pip install --no-cache-dir .

# Hardening: Bemfa cloud can never be enabled in this build.
RUN sed -i 's/^    bemfa_enabled = .*/    bemfa_enabled = False  # disabled by ha-cuktech wrapper/' /app/config.py \
    && grep -q 'bemfa_enabled = False' /app/config.py

# Hardening: do not fall back to a third-party CDN if the bundled Chart.js fails.
RUN printf '%s\n' \
    '// External CDN fallback disabled by ha-cuktech wrapper.' \
    'if (typeof Chart === "undefined") { console.error("Local Chart.js failed to load"); }' \
    > /app/web/static/chart-loader.js

COPY run.sh /run.sh
RUN chmod 0755 /run.sh

EXPOSE 8199
ENTRYPOINT ["/run.sh"]
