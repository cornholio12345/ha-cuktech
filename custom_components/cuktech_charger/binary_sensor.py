"""Binärsensoren für CUKTECH Charger."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CuktechMQTTCoordinator
from .base_entity import CB_TYPE_ALL, CB_TYPE_PORT, CuktechBaseEntity
from .const import DOMAIN, PORT_NAMES


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    entities = [CuktechPortActive(coord, entry, piid, name) for piid, name in PORT_NAMES.items()]
    entities.append(CuktechConnectionBinarySensor(coord, entry))
    async_add_entities(entities)


class CuktechPortActive(CuktechBaseEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.POWER

    def __init__(self, coord, entry, piid: int, port_name: str) -> None:
        self._piid = piid
        self._attr_unique_id = f"{entry.entry_id}_port_{piid}_active"
        self._attr_name = f"{port_name} aktiv"
        super().__init__(coord, entry, CB_TYPE_PORT)

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.port_data.get(str(self._piid))
        return None if data is None else bool(data.get("active", False))


class CuktechConnectionBinarySensor(CuktechBaseEntity, BinarySensorEntity):
    _attr_name = "BLE-Verbindung"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coord, entry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_ble_connected"
        super().__init__(coord, entry, CB_TYPE_ALL)

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.ble_connected
