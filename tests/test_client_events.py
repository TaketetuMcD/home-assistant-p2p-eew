from __future__ import annotations

import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock


COMPONENT_DIR = (
    Path(__file__).parents[1] / "custom_components" / "p2p_eew"
)


def _install_import_stubs() -> None:
    package = types.ModuleType("p2p_eew")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules.setdefault("p2p_eew", package)

    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientWebSocketResponse = object
    aiohttp.WSMsgType = types.SimpleNamespace(
        TEXT="text", CLOSED="closed", CLOSING="closing", ERROR="error"
    )
    sys.modules.setdefault("aiohttp", aiohttp)

    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    helpers = types.ModuleType("homeassistant.helpers")
    aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")
    aiohttp_client.async_get_clientsession = Mock()

    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.config_entries", config_entries)
    sys.modules.setdefault("homeassistant.core", core)
    sys.modules.setdefault("homeassistant.helpers", helpers)
    sys.modules.setdefault("homeassistant.helpers.aiohttp_client", aiohttp_client)


_install_import_stubs()
client_module = importlib.import_module("p2p_eew.client")
const = importlib.import_module("p2p_eew.const")


class FakeBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def async_fire(self, event_type: str, data: dict) -> None:
        self.events.append((event_type, data))


class FakeHass:
    def __init__(self) -> None:
        self.bus = FakeBus()


class FakeEntry:
    def __init__(self, data: dict, options: dict | None = None) -> None:
        self.data = data
        self.options = options or {}


def _payload(
    message_id: str,
    event_id: str,
    serial: int,
    pref: str = "神奈川",
    name: str = "神奈川県東部",
    scale_to: int = 45,
    cancelled: bool = False,
) -> dict:
    return {
        "id": message_id,
        "code": 556,
        "cancelled": cancelled,
        "issue": {
            "eventId": event_id,
            "serial": serial,
            "time": "2026/09/05 12:00:00",
        },
        "earthquake": {
            "originTime": "2026/09/05 11:59:50",
            "hypocenter": {
                "name": "テスト震源",
                "magnitude": 6.0,
                "depth": 20,
                "latitude": 35.0,
                "longitude": 139.0,
            },
        },
        "areas": [
            {
                "pref": pref,
                "name": name,
                "scaleFrom": 40,
                "scaleTo": scale_to,
                "kindCode": "10",
                "arrivalTime": "2026/09/05 12:00:10",
            }
        ],
    }


class ClientEventTests(unittest.IsolatedAsyncioTestCase):
    def _client(self, **overrides: object):
        data = {
            const.CONF_AREAS: ["神奈川県", "東京都"],
            const.CONF_MIN_SCALE: 45,
            const.CONF_NOTIFY_INTENSITY_INCREASE: True,
            **overrides,
        }
        hass = FakeHass()
        client = client_module.P2PEEWClient(hass, FakeEntry(data))
        client._schedule_clear = Mock()
        return hass, client

    async def test_later_report_can_cross_intensity_threshold(self) -> None:
        hass, client = self._client(min_scale=50)

        await client._handle_payload(_payload("m1", "e1", 1, scale_to=45))
        self.assertEqual(hass.bus.events, [])

        await client._handle_payload(_payload("m2", "e1", 2, scale_to=50))
        self.assertEqual([event[0] for event in hass.bus.events], [const.EVENT_WARNING])

    async def test_intensity_increase_emits_update_only_once(self) -> None:
        hass, client = self._client()

        await client._handle_payload(_payload("m1", "e1", 1, scale_to=45))
        await client._handle_payload(_payload("m2", "e1", 2, scale_to=50))
        await client._handle_payload(_payload("m3", "e1", 3, scale_to=50))

        self.assertEqual(
            [event[0] for event in hass.bus.events],
            [const.EVENT_WARNING, const.EVENT_UPDATE],
        )
        self.assertEqual(hass.bus.events[1][1]["previous_max_scale_to"], 45)

    async def test_update_can_be_disabled(self) -> None:
        hass, client = self._client(notify_intensity_increase=False)

        await client._handle_payload(_payload("m1", "e1", 1, scale_to=45))
        await client._handle_payload(_payload("m2", "e1", 2, scale_to=55))

        self.assertEqual([event[0] for event in hass.bus.events], [const.EVENT_WARNING])

    async def test_cancellation_only_fires_for_alerted_event(self) -> None:
        hass, client = self._client()

        await client._handle_payload(
            _payload("cancel-other", "other", 2, cancelled=True)
        )
        self.assertEqual(hass.bus.events, [])

        await client._handle_payload(_payload("m1", "e1", 1, scale_to=45))
        await client._handle_payload(_payload("cancel", "e1", 2, cancelled=True))

        self.assertEqual(
            [event[0] for event in hass.bus.events],
            [const.EVENT_WARNING, const.EVENT_CANCEL],
        )
        self.assertFalse(client.warning_active)


if __name__ == "__main__":
    unittest.main()
