"""Sensoren für CUKTECH Charger."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CuktechMQTTCoordinator
from .base_entity import CB_TYPE_PORT, CuktechBaseEntity
from .const import DOMAIN, PORT_MAP, PORT_NAMES, PROTOCOL_OPTIONS

_LOGGER = logging.getLogger(__name__)
LABELS = {"voltage": "Spannung", "current": "Strom", "power": "Leistung"}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    entities: list = []
    for piid, pname in PORT_NAMES.items():
        for sensor_type in ("voltage", "current", "power"):
            entities.append(CuktechPortSensor(coord, entry, piid, pname, sensor_type))
        entities.append(CuktechPortProtocolSensor(coord, entry, piid, pname))
    entities.append(CuktechTotalPowerSensor(coord, entry))
    async_add_entities(entities)


class CuktechPortSensor(CuktechBaseEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    UNITS = {
        "voltage": UnitOfElectricPotential.VOLT,
        "current": UnitOfElectricCurrent.AMPERE,
        "power": UnitOfPower.WATT,
    }

    def __init__(self, coord, entry, piid: int, port_name: str, sensor_type: str) -> None:
        self._piid = piid
        self._port_name = port_name
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{entry.entry_id}_port_{piid}_{sensor_type}"
        self._attr_name = f"{port_name} {LABELS[sensor_type]}"
        self._attr_native_unit_of_measurement = self.UNITS[sensor_type]
        super().__init__(coord, entry, CB_TYPE_PORT)

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.port_data.get(str(self._piid))
        if data is None:
            return None
        value = data.get(self._sensor_type)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            _LOGGER.warning("Ungültiger Messwert %s für %s: %r", self._sensor_type, self._port_name, value)
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.port_data.get(str(self._piid))
        return {} if data is None else {"port": self._port_name, "aktiv": data.get("active", False)}


class CuktechTotalPowerSensor(CuktechBaseEntity, SensorEntity):
    _attr_name = "Gesamtleistung"
    _attr_icon = "mdi:flash"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coord, entry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_total_power"
        super().__init__(coord, entry, CB_TYPE_PORT)

    @property
    def native_value(self) -> float:
        total = 0.0
        for piid in PORT_MAP.values():
            data = self.coordinator.port_data.get(str(piid))
            if data and data.get("active"):
                try:
                    total += float(data.get("power") or 0)
                except (TypeError, ValueError):
                    pass
        return round(total, 1)


class CuktechPortProtocolSensor(CuktechBaseEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = PROTOCOL_OPTIONS

    def __init__(self, coord, entry, piid: int, port_name: str) -> None:
        self._piid = piid
        self._port_name = port_name
        self._attr_unique_id = f"{entry.entry_id}_port_{piid}_protocol"
        self._attr_name = f"{port_name} Ladeprotokoll"
        self._attr_icon = "mdi:usb-c-port"
        super().__init__(coord, entry, CB_TYPE_PORT)

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.port_data.get(str(self._piid))
        if data is None:
            return None
        protocol = data.get("protocol", "idle")
        return protocol if protocol in PROTOCOL_OPTIONS else "Unknown"
