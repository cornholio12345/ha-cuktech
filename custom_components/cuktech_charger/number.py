"""Countdown-Werte für CUKTECH Charger."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CuktechMQTTCoordinator
from .base_entity import CB_TYPE_SETTINGS, CuktechBaseEntity
from .const import COUNTDOWN_PIIDS, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        CuktechCountdown(coord, entry, piid, cfg["name"], cfg["icon"])
        for piid, cfg in COUNTDOWN_PIIDS.items()
    ])


class CuktechCountdown(CuktechBaseEntity, NumberEntity):
    _attr_native_min_value = 0
    _attr_native_max_value = 1440
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"
    _attr_mode = NumberMode.BOX

    def __init__(self, coord, entry, piid: int, name: str, icon: str) -> None:
        self._piid = piid
        self._attr_unique_id = f"{entry.entry_id}_countdown_{piid}"
        self._attr_name = name
        self._attr_icon = icon
        super().__init__(coord, entry, CB_TYPE_SETTINGS)

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        value = self.coordinator.data.get(str(self._piid))
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_value(self._piid, int(value))
