from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .client import P2PEEWClient
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    client: P2PEEWClient = entry.runtime_data
    async_add_entities(
        [
            P2PEEWWarningSensor(entry, client),
            P2PEEWConnectionSensor(entry, client),
        ]
    )


class P2PEEWBaseSensor(BinarySensorEntity):
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, client: P2PEEWClient) -> None:
        self.entry = entry
        self.client = client
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="緊急地震速報",
            manufacturer="P2P地震情報",
            model="WebSocket EEW",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.client.add_listener(self._handle_update))

    def _handle_update(self) -> None:
        self.async_write_ha_state()


class P2PEEWWarningSensor(P2PEEWBaseSensor):
    _attr_name = "EEW警報"
    _attr_icon = "mdi:alert-octagon"
    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, client: P2PEEWClient) -> None:
        super().__init__(entry, client)
        self._attr_unique_id = f"{entry.entry_id}_warning"
        self._attr_suggested_object_id = "p2p_eew_warning"

    @property
    def is_on(self) -> bool:
        return self.client.warning_active

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.client.last_warning


class P2PEEWConnectionSensor(P2PEEWBaseSensor):
    _attr_name = "接続"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_registry_enabled_default = True
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, client: P2PEEWClient) -> None:
        super().__init__(entry, client)
        self._attr_unique_id = f"{entry.entry_id}_connection"
        self._attr_suggested_object_id = "p2p_eew_connection"

    @property
    def is_on(self) -> bool:
        return self.client.connected
