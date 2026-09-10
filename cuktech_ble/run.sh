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
  enabled: false
  host: "core-mosquitto"
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

# Enforce local-safe settings on every start while preserving user BLE/MQTT config.
python3 - <<'PY'
from pathlib import Path
import yaml

p = Path('/data/config.yaml')
cfg = yaml.safe_load(p.read_text()) or {}

cfg.setdefault('bemfa', {})['enabled'] = False
server = cfg.setdefault('server', {})
server['host'] = '0.0.0.0'
server['port'] = 8199
server['history_db_path'] = '/data/port_history.db'

p.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
PY

exec python3 /app/ha_server.py
