"""CUKTECH Charger integration for Home Assistant - local MQTT bridge."""
from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from typing import Any

import homeassistant.components.mqtt as mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    BLE_OPERATION_TIMEOUT,
    CHARGE_EVENT_BUFFER,
    CONF_SERVER_URL,
    DEFAULT_SERVER_URL,
    DEVICE_INFO,
    DOMAIN,
    HEALTH_CHECK_INTERVAL,
    HTTP_TIMEOUT,
    PORT_MAP,
    STATUS_STALE_SECONDS,
    TOPIC_CHARGE_EVENT,
    TOPIC_PORT,
    TOPIC_PREFIX,
    TOPIC_SET,
    TOPIC_SETTINGS,
    TOPIC_STATUS,
)
from .protocol_codec import decode_protocol_switches, encode_protocol_switches

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.EVENT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    coordinator = CuktechMQTTCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator
    try:
        await coordinator.async_setup()
    except ConfigEntryNotReady:
        raise
    except Exception as err:
        _LOGGER.exception("CUKTECH-Koordinator konnte nicht gestartet werden")
        raise ConfigEntryNotReady from err
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        await coordinator.async_unload()
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


class CuktechMQTTCoordinator:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.server_url = entry.data.get(CONF_SERVER_URL, DEFAULT_SERVER_URL)
        self._port_data: dict[str, dict[str, Any]] = {}
        self._settings: dict[str, Any] = {}
        self._callbacks: list = []
        self._port_callbacks: list = []
        self._settings_callbacks: list = []
        self._charge_event_callbacks: list = []
        self._unsub: list = []
        self._available = False
        self._mqtt_connected = False
        self._health_check_unsub = None
        self._last_status_time: float = -999
        self._health_failures = 0
        self._device_model = DEVICE_INFO["model"]
        self._firmware_version = ""
        self._ble_connected = False
        self._ble_enabled = False
        self._ble_pending = False
        self._ble_lock = asyncio.Lock()
        self._ble_timeout_task: asyncio.Task | None = None
        self._charge_events: deque[dict] = deque(maxlen=CHARGE_EVENT_BUFFER)
        self._charge_event_keys: set = set()
        self._charge_event_key_order: deque = deque()

    @property
    def available(self) -> bool:
        return self._available

    @property
    def ble_connected(self) -> bool:
        return self._ble_connected

    @property
    def ble_enabled(self) -> bool:
        return self._ble_enabled

    @property
    def ble_pending(self) -> bool:
        return self._ble_pending

    @property
    def last_charge_event(self) -> dict | None:
        return self._charge_events[-1] if self._charge_events else None

    @property
    def port_data(self) -> dict[str, dict[str, Any]]:
        return dict(self._port_data)

    @property
    def data(self) -> dict[str, Any]:
        return dict(self._settings)

    @property
    def protocol_switches(self) -> dict[str, dict[str, bool]]:
        return decode_protocol_switches(self._settings.get("21", 0))

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            **DEVICE_INFO,
            "model": self._device_model or DEVICE_INFO["model"],
            "sw_version": self._firmware_version,
        }

    def register_callback(self, cb) -> None:
        self._callbacks.append(cb)

    def unregister_callback(self, cb) -> None:
        if cb in self._callbacks:
            self._callbacks.remove(cb)

    def register_port_callback(self, cb) -> None:
        self._port_callbacks.append(cb)

    def unregister_port_callback(self, cb) -> None:
        if cb in self._port_callbacks:
            self._port_callbacks.remove(cb)

    def register_settings_callback(self, cb) -> None:
        self._settings_callbacks.append(cb)

    def unregister_settings_callback(self, cb) -> None:
        if cb in self._settings_callbacks:
            self._settings_callbacks.remove(cb)

    def register_charge_event_callback(self, cb) -> None:
        self._charge_event_callbacks.append(cb)

    def unregister_charge_event_callback(self, cb) -> None:
        if cb in self._charge_event_callbacks:
            self._charge_event_callbacks.remove(cb)

    def _notify_callbacks(self, callbacks: list | None = None) -> None:
        for cb in list(callbacks if callbacks is not None else self._callbacks):
            try:
                cb()
            except Exception:
                _LOGGER.exception("Fehler in CUKTECH-Callback")

    def _notify_all(self) -> None:
        self._notify_callbacks(self._callbacks)
        self._notify_callbacks(self._port_callbacks)
        self._notify_callbacks(self._settings_callbacks)

    async def async_setup(self) -> None:
        if not await mqtt.async_wait_for_mqtt_client(self.hass):
            raise ConfigEntryNotReady("MQTT ist nicht verfügbar")

        for port_name in PORT_MAP:
            self._unsub.append(await mqtt.async_subscribe(
                self.hass, f"{TOPIC_PORT}/{port_name}", self._on_port_message
            ))
        self._unsub.append(await mqtt.async_subscribe(self.hass, TOPIC_SETTINGS, self._on_settings_message))
        self._unsub.append(await mqtt.async_subscribe(self.hass, TOPIC_STATUS, self._on_status_message))
        self._unsub.append(await mqtt.async_subscribe(self.hass, TOPIC_CHARGE_EVENT, self._on_charge_event))

        self._last_status_time = self.hass.loop.time()
        self._health_check_unsub = async_track_time_interval(
            self.hass, self._async_health_check, HEALTH_CHECK_INTERVAL
        )
        await self._async_health_check(None)
        if self._ble_connected and not self._ble_enabled:
            self._ble_enabled = True
        _LOGGER.info("CUKTECH Charger MQTT-Koordinator gestartet")

    async def async_unload(self) -> None:
        if self._ble_timeout_task is not None and not self._ble_timeout_task.done():
            self._ble_timeout_task.cancel()
        for unsub in self._unsub:
            unsub()
        self._unsub.clear()
        if self._health_check_unsub:
            self._health_check_unsub()
        self._health_check_unsub = None

    def _sync_device_info_from_payload(self, payload: dict) -> bool:
        changed = False
        if payload.get("device_model") and self._device_model != payload["device_model"]:
            self._device_model = payload["device_model"]
            changed = True
        if "firmware_version" in payload:
            new_fw = payload.get("firmware_version", "")
            if self._firmware_version != new_fw:
                self._firmware_version = new_fw
                changed = True
        return changed

    def _sync_ble_state(self, connected: bool) -> bool:
        prev_enabled = self._ble_enabled
        prev_connected = self._ble_connected
        self._ble_connected = connected
        if connected:
            self._ble_enabled = True
        elif self._ble_enabled:
            self._ble_enabled = False
        if prev_connected and not connected:
            self._port_data = {}
            self._notify_callbacks(self._port_callbacks)
        return prev_enabled != self._ble_enabled

    def _clear_pending_if_confirmed(self) -> None:
        if self._ble_pending and self._ble_connected == self._ble_enabled:
            self._ble_pending = False

    def _update_availability(self) -> None:
        http_recent = (self.hass.loop.time() - self._last_status_time) < STATUS_STALE_SECONDS
        self._available = self._mqtt_connected or http_recent

    @callback
    def _on_port_message(self, msg: Any) -> None:
        try:
            payload = json.loads(msg.payload)
            if not isinstance(payload, dict):
                return
            piid = PORT_MAP.get(msg.topic.split("/")[-1])
            if piid:
                self._port_data[str(piid)] = payload
                self._notify_callbacks(self._port_callbacks)
        except Exception as err:
            _LOGGER.debug("Portdaten konnten nicht verarbeitet werden: %s", err)

    @callback
    def _on_settings_message(self, msg: Any) -> None:
        try:
            payload = json.loads(msg.payload)
            if isinstance(payload, dict):
                self._settings = payload
                self._notify_callbacks(self._settings_callbacks)
        except Exception as err:
            _LOGGER.debug("Einstellungen konnten nicht verarbeitet werden: %s", err)

    @callback
    def _on_status_message(self, msg: Any) -> None:
        try:
            payload = json.loads(msg.payload)
            if not isinstance(payload, dict):
                return
            prev_connected = self._ble_connected
            connected = bool(payload.get("connected", False))
            self._mqtt_connected = connected
            if connected:
                self._last_status_time = self.hass.loop.time()
                self._health_failures = 0
            info_changed = self._sync_device_info_from_payload(payload)
            self._sync_ble_state(connected)
            self._clear_pending_if_confirmed()
            self._update_availability()
            if info_changed or prev_connected != connected:
                self.hass.async_create_task(self._async_update_device_registry())
            self._notify_callbacks(self._callbacks)
        except Exception as err:
            _LOGGER.debug("Status konnte nicht verarbeitet werden: %s", err)

    @callback
    def _on_charge_event(self, msg: Any) -> None:
        try:
            payload = json.loads(msg.payload)
            if not isinstance(payload, dict) or payload.get("event") != "charge_end":
                return
            key = (payload.get("port"), payload.get("end_time"))
            if key in self._charge_event_keys:
                return
            self._charge_event_keys.add(key)
            self._charge_event_key_order.append(key)
            while len(self._charge_event_keys) > CHARGE_EVENT_BUFFER:
                self._charge_event_keys.discard(self._charge_event_key_order.popleft())
            self._charge_events.append(payload)
            self._notify_callbacks(self._charge_event_callbacks)
        except Exception as err:
            _LOGGER.debug("Ladeereignis konnte nicht verarbeitet werden: %s", err)

    async def _async_update_device_registry(self) -> None:
        from homeassistant.helpers import device_registry as dr
        dev_reg = dr.async_get(self.hass)
        device = dev_reg.async_get_device(identifiers={(DOMAIN, self.entry.entry_id)})
        if device is not None:
            dev_reg.async_update_device(
                device.id,
                sw_version=self._firmware_version or None,
                model=self._device_model or None,
            )

    async def _async_health_check(self, _now) -> None:
        session = async_get_clientsession(self.hass)
        was_available = self._available
        try:
            async with session.get(f"{self.server_url}/api/status", timeout=HTTP_TIMEOUT) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._last_status_time = self.hass.loop.time()
                    self._health_failures = 0
                    self._update_availability()
                    if not self._mqtt_connected and isinstance(data, dict):
                        info_changed = self._sync_device_info_from_payload(data)
                        connected = bool(data.get("connected", False))
                        self._sync_ble_state(connected)
                        self._clear_pending_if_confirmed()
                        if info_changed:
                            self.hass.async_create_task(self._async_update_device_registry())
                else:
                    await resp.read()
                    self._available = self._mqtt_connected
        except Exception:
            self._available = self._mqtt_connected
            self._health_failures += 1
        if self._available != was_available:
            self._notify_all()

    async def async_enable_ble(self, enable: bool) -> bool:
        async with self._ble_lock:
            previous = self._ble_enabled
            self._ble_enabled = enable
            self._ble_pending = True
            self._notify_callbacks(self._callbacks)
            success = False
            try:
                await mqtt.async_publish(
                    self.hass,
                    f"{TOPIC_PREFIX}/ble",
                    json.dumps({"enabled": enable}),
                )
                success = True
            except Exception:
                pass
            if not success:
                try:
                    session = async_get_clientsession(self.hass)
                    async with session.post(
                        f"{self.server_url}/api/enable",
                        json={"enabled": enable},
                        timeout=BLE_OPERATION_TIMEOUT,
                    ) as resp:
                        success = resp.status == 200
                except Exception:
                    pass
            self._ble_pending = False
            if not success:
                self._ble_enabled = previous
            self._notify_callbacks(self._callbacks)
            return success

    async def async_set_value(self, piid: int, value: Any) -> None:
        await mqtt.async_publish(self.hass, TOPIC_SET, json.dumps({"piid": piid, "value": value}))

    async def async_port_control(self, port: str, action: str) -> None:
        await mqtt.async_publish(self.hass, TOPIC_PORT, json.dumps({"port": port, "action": action}))

    async def async_set_protocol(self, port: str, protocol: str, on: bool) -> None:
        async with self._ble_lock:
            switches = self.protocol_switches
            if port not in switches or protocol not in switches[port]:
                _LOGGER.error("Unbekanntes Ladeprotokoll: %s.%s", port, protocol)
                return
            switches[port][protocol] = on
            await self.async_set_value(21, encode_protocol_switches(switches))
