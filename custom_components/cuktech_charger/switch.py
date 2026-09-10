"""Schalter für CUKTECH Charger."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CuktechMQTTCoordinator
from .base_entity import CB_TYPE_ALL, CB_TYPE_SETTINGS, CuktechBaseEntity
from .const import DOMAIN, PORT_SWITCHES, PROTOCOL_SWITCHES, SETTING_PIIDS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    entities = [CuktechConnectionSwitch(coord, entry)]
    for piid, cfg in SETTING_PIIDS.items():
        entities.append(CuktechSettingSwitch(coord, entry, piid, cfg["name"], cfg["icon"]))
    for port, cfg in PORT_SWITCHES.items():
        entities.append(CuktechPortSwitch(coord, entry, port, cfg["name"], cfg["icon"], cfg["bit"]))
    for port, proto, name in PROTOCOL_SWITCHES:
        entities.append(CuktechProtocolSwitch(coord, entry, port, proto, name))
    async_add_entities(entities)


class CuktechConnectionSwitch(CuktechBaseEntity, SwitchEntity):
    _attr_name = "BLE-Verbindung steuern"
    _attr_icon = "mdi:bluetooth-connect"

    def __init__(self, coord, entry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_ble_control"
        super().__init__(coord, entry, CB_TYPE_ALL)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"ausstehend": self.coordinator.ble_pending}

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.ble_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_enable_ble(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_enable_ble(False)


class CuktechSettingSwitch(CuktechBaseEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coord, entry, piid: int, name: str, icon: str) -> None:
        self._piid = piid
        self._attr_unique_id = f"{entry.entry_id}_switch_{piid}"
        self._attr_name = name
        self._attr_icon = icon
        super().__init__(coord, entry, CB_TYPE_SETTINGS)

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        value = self.coordinator.data.get(str(self._piid))
        if value is None:
            return None
        try:
            return int(value) != 0
        except (TypeError, ValueError):
            _LOGGER.warning("Ungültiger Einstellungswert für PIID %s: %r", self._piid, value)
            return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_value(self._piid, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_value(self._piid, 0)


class CuktechPortSwitch(CuktechBaseEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.OUTLET

    def __init__(self, coord, entry, port: str, name: str, icon: str, bit: int) -> None:
        self._port = port
        self._bit = bit
        self._attr_unique_id = f"{entry.entry_id}_port_switch_{port}"
        self._attr_name = name
        self._attr_icon = icon
        super().__init__(coord, entry, CB_TYPE_SETTINGS)

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        port_ctl = self.coordinator.data.get("16")
        if port_ctl is None:
            return None
        try:
            port_ctl = int(port_ctl)
        except (TypeError, ValueError):
            return None
        return bool(port_ctl & (1 << self._bit))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_port_control(self._port, "on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_port_control(self._port, "off")


class CuktechProtocolSwitch(CuktechBaseEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coord, entry, port: str, protocol: str, name: str) -> None:
        self._port = port
        self._protocol = protocol
        self._attr_unique_id = f"{entry.entry_id}_protocol_{port}_{protocol}"
        self._attr_name = name
        self._attr_icon = "mdi:power-plug-outline"
        super().__init__(coord, entry, CB_TYPE_SETTINGS)

    @property
    def is_on(self) -> bool | None:
        port_data = self.coordinator.protocol_switches.get(self._port)
        if port_data is None:
            return None
        if self._protocol == "pps" and port_data.get("pd") is False:
            return False
        return port_data.get(self._protocol)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_protocol(self._port, self._protocol, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_protocol(self._port, self._protocol, False)
