"""Auswahlfelder für CUKTECH Charger."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CuktechMQTTCoordinator
from .base_entity import CB_TYPE_SETTINGS, CuktechBaseEntity
from .const import DOMAIN, PIID_DISPLAY, SELECT_OPTION_MAP, SELECT_PIIDS


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        CuktechSelect(coord, entry, piid, cfg["name"], cfg["icon"], cfg["options"])
        for piid, cfg in SELECT_PIIDS.items()
    ])


class CuktechSelect(CuktechBaseEntity, SelectEntity):
    def __init__(self, coord, entry, piid: int, name: str, icon: str, options: list[str]) -> None:
        self._piid = piid
        self._attr_unique_id = f"{entry.entry_id}_select_{piid}"
        self._attr_name = name
        self._attr_icon = icon
        self._attr_options = options
        super().__init__(coord, entry, CB_TYPE_SETTINGS)

    @property
    def current_option(self) -> str | None:
        if not self.coordinator.data:
            return None
        value = self.coordinator.data.get(str(self._piid))
        if value is None:
            return None
        return PIID_DISPLAY.get(self._piid, {}).get(value)

    async def async_select_option(self, option: str) -> None:
        value = SELECT_OPTION_MAP.get(self._piid, {}).get(option)
        if value is not None:
            await self.coordinator.async_set_value(self._piid, value)
