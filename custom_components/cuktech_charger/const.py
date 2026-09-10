"""Constants for the CUKTECH Charger Home Assistant integration."""
from datetime import timedelta

DOMAIN = "cuktech_charger"
CONF_SERVER_URL = "server_url"
DEFAULT_SERVER_URL = "http://localhost:8199"

TOPIC_PREFIX = "cuktech/charger"
TOPIC_PORT = f"{TOPIC_PREFIX}/port"
TOPIC_SETTINGS = f"{TOPIC_PREFIX}/settings"
TOPIC_STATUS = f"{TOPIC_PREFIX}/status"
TOPIC_SET = f"{TOPIC_PREFIX}/set"
TOPIC_CHARGE_EVENT = f"{TOPIC_PREFIX}/charge_event"

PORT_MAP = {"c1": 1, "c2": 2, "c3": 3, "a": 4}
PORT_NAMES = {1: "C1", 2: "C2", 3: "C3", 4: "USB-A"}

PIID_NAMES = {
    1: "C1-Portdaten",
    2: "C2-Portdaten",
    3: "C3-Portdaten",
    4: "USB-A-Portdaten",
    5: "Szenenmodus",
    6: "Display-Abschaltzeit",
    7: "Protokollsteuerung",
    8: "Countdown-Einstellung",
    9: "C1-Countdown",
    10: "C2-Countdown",
    11: "C3-Countdown",
    12: "USB-A-Countdown",
    13: "Sprache",
    14: "Ansicht",
    15: "USB-A-Niedrigstrommodus",
    16: "Portsteuerung",
    19: "Display bei Leerlauf aus",
    20: "Bildschirmausrichtung sperren",
}

# Raw MIOT values -> German display text. Keep numeric values unchanged.
PIID_DISPLAY = {
    5: {1: "KI-Modus", 2: "Digital-Ökosystem", 3: "Einzelport-Priorität", 4: "Ausgewogen"},
    6: {1: "5 Minuten", 2: "10 Minuten", 3: "30 Minuten", 4: "Immer an", 5: "1 Minute"},
    7: None,
    13: {0: "Englisch", 1: "Chinesisch"},
    15: {0: "Aus", 1: "Ein"},
    19: {0: "Aus", 1: "Ein"},
    20: {0: "Aus", 1: "Ein"},
}

SELECT_PIIDS = {
    5: {"name": "Szenenmodus", "icon": "mdi:cog", "options": ["KI-Modus", "Digital-Ökosystem", "Einzelport-Priorität", "Ausgewogen"]},
    6: {"name": "Display-Abschaltzeit", "icon": "mdi:monitor", "options": ["1 Minute", "5 Minuten", "10 Minuten", "30 Minuten", "Immer an"]},
    13: {"name": "Sprache", "icon": "mdi:translate", "options": ["Englisch", "Chinesisch"]},
}

SELECT_OPTION_MAP = {}
for piid, cfg in SELECT_PIIDS.items():
    display = PIID_DISPLAY.get(piid, {})
    option_map = {}
    for k, v in display.items():
        if v in cfg["options"] and v not in option_map:
            option_map[v] = k
    SELECT_OPTION_MAP[piid] = option_map

PROTOCOL_BITS = {
    "c1": {"pd": 0, "pps": 1, "ufcs": 2},
    "c2": {"pd": 8, "pps": 9, "ufcs": 10},
    "c3": {"ufcs": 16, "scp": 17},
    "a": {"ufcs": 24, "scp": 25},
}

PROTOCOL_SWITCHES = [
    ("c1", "pd", "C1 PD"),
    ("c1", "pps", "C1 PPS"),
    ("c1", "ufcs", "C1 UFCS"),
    ("c2", "pd", "C2 PD"),
    ("c2", "pps", "C2 PPS"),
    ("c2", "ufcs", "C2 UFCS"),
    ("c3", "ufcs", "C3 UFCS"),
    ("c3", "scp", "C3 SCP"),
    ("a", "ufcs", "USB-A UFCS"),
    ("a", "scp", "USB-A SCP"),
]

SETTING_PIIDS = {
    15: {"name": "USB-A-Niedrigstrommodus", "icon": "mdi:usb-port"},
    19: {"name": "Display bei Leerlauf aus", "icon": "mdi:monitor-off"},
    20: {"name": "Bildschirmausrichtung sperren", "icon": "mdi:screen-rotation-lock"},
}

PORT_SWITCHES = {
    "c1": {"name": "C1-Port", "icon": "mdi:usb-c-port", "bit": 0},
    "c2": {"name": "C2-Port", "icon": "mdi:usb-c-port", "bit": 1},
    "c3": {"name": "C3-Port", "icon": "mdi:usb-c-port", "bit": 2},
    "a": {"name": "USB-A-Port", "icon": "mdi:usb-port", "bit": 3},
}

COUNTDOWN_PIIDS = {
    9: {"name": "C1-Countdown", "icon": "mdi:timer-cog-outline"},
    10: {"name": "C2-Countdown", "icon": "mdi:timer-cog-outline"},
    11: {"name": "C3-Countdown", "icon": "mdi:timer-cog-outline"},
    12: {"name": "USB-A-Countdown", "icon": "mdi:timer-cog-outline"},
}

PROTOCOL_OPTIONS = ["idle", "5V", "QC", "AFC", "FCP", "SCP", "PD", "PPS", "UFCS", "Unknown"]

DEVICE_INFO = {
    "name": "CUKTECH 10 Ultra",
    "manufacturer": "CUKTECH",
    "model": "njcuk.fitting.ad1204",
    "sw_version": "",
}

HEALTH_CHECK_INTERVAL = timedelta(seconds=30)
HTTP_TIMEOUT = 10
BLE_OPERATION_TIMEOUT = 30
CHARGE_EVENT_BUFFER = 50
STATUS_STALE_SECONDS = 30
