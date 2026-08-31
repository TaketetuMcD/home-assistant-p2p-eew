from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    async_add_entities([P2PEEWTestButton(entry, client)])


class P2PEEWTestButton(ButtonEntity):
    _attr_name = "EEWテスト"
    _attr_icon = "mdi:alarm-light"
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, client: P2PEEWClient) -> None:
        self.client = client
        self._attr_unique_id = f"{entry.entry_id}_test"
        self._attr_suggested_object_id = "p2p_eew_test"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="緊急地震速報",
            manufacturer="P2P地震情報",
            model="WebSocket EEW",
        )

    async def async_press(self) -> None:
        await self.client.async_test_warning()
