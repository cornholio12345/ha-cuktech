#!/bin/sh
set -eu

CONFIG=/data/config.yaml
mkdir -p /data

if [ ! -f "$CONFIG" ]; then
cat > "$CONFIG" <<'EOF'
ble:
  mac: "XX:XX:XX:XX:XX:XX"
  token: ""
  ble_key: ""
  scan_timeout: 15

mqtt:
  enabled: true
  host: ""
  port: 1883
  username: ""
  password: ""
  keepalive: 60
  topic_prefix: "cuktech/charger"

server:
  host: "0.0.0.0"
  port: 8199
  command_timeout: 10.0
  reconnect_base_delay: 1.0
  reconnect_max_delay: 300.0
  settings_refresh_interval: 10.0
  log_level: "info"
  history_retention_days: 2
  history_db_path: "/data/port_history.db"

bemfa:
  enabled: false
  uid: ""
EOF
fi

# Enforce local-safe settings and inject Supervisor-managed MQTT credentials.
python3 - <<'PY'
from pathlib import Path
import json
import os
import urllib.request
import yaml

p = Path('/data/config.yaml')
cfg = yaml.safe_load(p.read_text()) or {}

cfg.setdefault('bemfa', {})['enabled'] = False
server = cfg.setdefault('server', {})
server['host'] = '0.0.0.0'
server['port'] = 8199
server['history_db_path'] = '/data/port_history.db'

mqtt = cfg.setdefault('mqtt', {})
try:
    token = os.environ['SUPERVISOR_TOKEN']
    req = urllib.request.Request(
        'http://supervisor/services/mqtt',
        headers={'Authorization': f'Bearer {token}'},
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        payload = json.load(r)
    svc = payload.get('data', payload)
    mqtt['enabled'] = True
    mqtt['host'] = svc['host']
    mqtt['port'] = int(svc['port'])
    mqtt['username'] = svc.get('username', '')
    mqtt['password'] = svc.get('password', '')
    print(f"[ha-cuktech] MQTT service injected: {mqtt['host']}:{mqtt['port']}")
except Exception as e:
    print(f"[ha-cuktech] MQTT service lookup failed: {e}")

p.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
PY

exec python3 /app/ha_server.py
