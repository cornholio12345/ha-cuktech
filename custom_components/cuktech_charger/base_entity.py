"""Gemeinsame Basis für CUKTECH-Entitäten."""
from __future__ import annotations

from typing import Any
from homeassistant.core import callback
from .const import DOMAIN

CB_TYPE_PORT = "port"
CB_TYPE_SETTINGS = "settings"
CB_TYPE_ALL = "all"
CB_TYPE_CHARGE = "charge"


class CuktechBaseEntity:
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, callback_type: str = CB_TYPE_ALL, **kwargs) -> None:
        self.coordinator = coordinator
        self._entry = entry
        self._callback_type = callback_type
        super().__init__(**kwargs)
        if callback_type == CB_TYPE_PORT:
            coordinator.register_port_callback(self._update)
        elif callback_type == CB_TYPE_SETTINGS:
            coordinator.register_settings_callback(self._update)
        elif callback_type == CB_TYPE_CHARGE:
            coordinator.register_charge_event_callback(self._update)
        else:
            coordinator.register_callback(self._update)

    async def async_will_remove_from_hass(self) -> None:
        if self._callback_type == CB_TYPE_PORT:
            self.coordinator.unregister_port_callback(self._update)
        elif self._callback_type == CB_TYPE_SETTINGS:
            self.coordinator.unregister_settings_callback(self._update)
        elif self._callback_type == CB_TYPE_CHARGE:
            self.coordinator.unregister_charge_event_callback(self._update)
        else:
            self.coordinator.unregister_callback(self._update)
        await super().async_will_remove_from_hass()

    @callback
    def _update(self) -> None:
        if self.hass is not None:
            self.async_write_ha_state()

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            **self.coordinator.device_info,
        }

    @property
    def available(self) -> bool:
        return self.coordinator.available
