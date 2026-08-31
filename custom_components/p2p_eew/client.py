from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from aiohttp import ClientWebSocketResponse, WSMsgType

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    AUTO_CLEAR_SECONDS,
    CONF_AREA,
    EVENT_CANCEL,
    EVENT_WARNING,
    HISTORY_URL,
    RECOVERY_LIMIT,
    RECOVERY_MAX_AGE_SECONDS,
    TEST_CLEAR_SECONDS,
    WS_URL,
)

_LOGGER = logging.getLogger(__name__)
JST = timezone(timedelta(hours=9))


class P2PEEWClient:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.area = str(entry.data.get(CONF_AREA, "")).strip()

        self.connected = False
        self.warning_active = False
        self.last_warning: dict[str, Any] = {}

        self._listeners: set[Callable[[], None]] = set()
        self._stop = False
        self._ws: ClientWebSocketResponse | None = None
        self._clear_task: asyncio.Task | None = None

        # `id` removes duplicate delivery of exactly the same P2P message.
        self._seen_ids: set[str] = set()

        # IMPORTANT:
        # An eventId is added here ONLY AFTER the configured area actually
        # becomes a warning target. Therefore:
        #   report 1: target absent -> no alert
        #   report 2: target added  -> first alert
        #   later reports           -> no duplicate alert
        self._alerted_event_ids: set[str] = set()

    def add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(callback)

        def _remove() -> None:
            self._listeners.discard(callback)

        return _remove

    def _notify(self) -> None:
        for callback in tuple(self._listeners):
            callback()

    def _set_connected(self, value: bool) -> None:
        if self.connected != value:
            self.connected = value
            self._notify()

    async def async_run(self) -> None:
        session = async_get_clientsession(self.hass)
        backoff = 1

        while not self._stop:
            try:
                async with session.ws_connect(WS_URL, heartbeat=30) as ws:
                    self._ws = ws
                    self._set_connected(True)
                    backoff = 1
                    _LOGGER.info("Connected to P2PQuake EEW WebSocket")

                    # P2P does not replay messages missed during an outage.
                    # Recover the latest still-relevant warning immediately
                    # after every connection/reconnection.
                    await self._async_recover_recent_warning()

                    async for msg in ws:
                        if self._stop:
                            break
                        if msg.type == WSMsgType.TEXT:
                            try:
                                payload = json.loads(msg.data)
                            except json.JSONDecodeError:
                                continue
                            await self._handle_payload(payload)
                        elif msg.type in (
                            WSMsgType.CLOSED,
                            WSMsgType.CLOSING,
                            WSMsgType.ERROR,
                        ):
                            break

            except asyncio.CancelledError:
                raise
            except Exception as err:
                if not self._stop:
                    _LOGGER.warning("P2PQuake WebSocket error: %s", err)
            finally:
                self._ws = None
                self._set_connected(False)

            if not self._stop:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    async def async_stop(self) -> None:
        self._stop = True
        if self._clear_task and not self._clear_task.done():
            self._clear_task.cancel()
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        self._set_connected(False)

    @staticmethod
    def _normalise_area(value: Any) -> str:
        return str(value or "").replace(" ", "").replace("　", "").strip()

    def _matches_area(self, area: dict[str, Any]) -> bool:
        if not self.area:
            return True

        target = self._normalise_area(self.area)
        pref = self._normalise_area(area.get("pref"))
        name = self._normalise_area(area.get("name"))

        # Exact match is preferred. For convenience, specifying a prefecture
        # such as "神奈川県" also matches its finer subdivisions. Empty values
        # are never considered matches.
        if pref and target == pref:
            return True
        if name and target == name:
            return True

        # A prefecture-level target should match all its subdivisions.
        if pref and target == pref:
            return True

        # Accommodate labels such as "神奈川県東部" when the API's pref/name
        # split differs slightly, while never treating an empty string as a hit.
        if pref and target.startswith(pref):
            if name and (target == name or target.endswith(name)):
                return True

        return False

    @staticmethod
    def _parse_issue_time(value: Any) -> datetime | None:
        if not value:
            return None
        text = str(value).strip()
        for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                dt = datetime.strptime(text, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=JST)
                return dt
            except ValueError:
                pass
        try:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=JST)
            return dt
        except ValueError:
            return None

    async def _async_recover_recent_warning(self) -> None:
        """Recover a current warning after a short WebSocket interruption.

        Only the newest report for each event is considered. If that newest
        report is a cancellation, the event is not replayed.
        """
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                HISTORY_URL,
                params={"codes": "556", "limit": str(RECOVERY_LIMIT)},
                timeout=5,
            ) as response:
                if response.status != 200:
                    _LOGGER.warning(
                        "EEW recovery history returned HTTP %s", response.status
                    )
                    return
                history = await response.json()
        except asyncio.CancelledError:
            raise
        except Exception as err:
            _LOGGER.warning("EEW recovery history failed: %s", err)
            return

        if not isinstance(history, list):
            return

        now = datetime.now(JST)
        newest_by_event: dict[str, dict[str, Any]] = {}

        for item in history:
            if not isinstance(item, dict) or item.get("code") != 556:
                continue
            if item.get("test") is True:
                continue

            issue = item.get("issue") or {}
            event_id = str(issue.get("eventId") or "")
            if not event_id:
                continue

            issue_dt = self._parse_issue_time(issue.get("time"))
            if issue_dt is None:
                continue

            age = (now - issue_dt.astimezone(JST)).total_seconds()
            if age < -30 or age > RECOVERY_MAX_AGE_SECONDS:
                continue

            old = newest_by_event.get(event_id)
            if old is None:
                newest_by_event[event_id] = item
                continue

            old_issue = old.get("issue") or {}
            old_dt = self._parse_issue_time(old_issue.get("time"))
            if old_dt is None or issue_dt > old_dt:
                newest_by_event[event_id] = item
                continue

            # If times are identical, prefer the larger serial when numeric.
            if issue_dt == old_dt:
                try:
                    new_serial = int(issue.get("serial") or 0)
                    old_serial = int(old_issue.get("serial") or 0)
                except (TypeError, ValueError):
                    new_serial = old_serial = 0
                if new_serial > old_serial:
                    newest_by_event[event_id] = item

        for item in newest_by_event.values():
            # Never resurrect an event whose newest information is cancellation.
            if item.get("cancelled") is True:
                continue
            await self._handle_payload(item, recovered=True)

    async def _handle_payload(
        self, data: dict[str, Any], recovered: bool = False
    ) -> None:
        if data.get("code") != 556:
            return

        # P2P-side test bulletins are not real warnings.
        if data.get("test") is True:
            return

        message_id = str(data.get("id") or "")
        if message_id:
            if message_id in self._seen_ids:
                return
            self._seen_ids.add(message_id)
            if len(self._seen_ids) > 500:
                self._seen_ids.pop()

        issue = data.get("issue") or {}
        event_id = str(issue.get("eventId") or "")
        serial = str(issue.get("serial") or "")

        if data.get("cancelled") is True:
            if event_id and event_id == self.last_warning.get("event_id"):
                self.warning_active = False
                self._notify()
            self.hass.bus.async_fire(
                EVENT_CANCEL,
                {
                    "event_id": event_id,
                    "serial": serial,
                    "area_filter": self.area,
                },
            )
            return

        # Evaluate the configured area on EVERY report.
        # Do not deduplicate by eventId before this point.
        areas = data.get("areas") or []
        matched_areas = [
            a for a in areas
            if isinstance(a, dict) and self._matches_area(a)
        ]

        if self.area and not matched_areas:
            _LOGGER.debug(
                "EEW %s report %s does not yet include target area %s",
                event_id,
                serial,
                self.area,
            )
            return

        source_areas = matched_areas if matched_areas else areas
        scale_from = max(
            (
                int(a.get("scaleFrom", -1))
                for a in source_areas
                if isinstance(a, dict)
            ),
            default=-1,
        )
        scale_to = max(
            (
                int(a.get("scaleTo", -1))
                for a in source_areas
                if isinstance(a, dict)
            ),
            default=-1,
        )

        earthquake = data.get("earthquake") or {}
        hypocenter = earthquake.get("hypocenter") or {}

        details: dict[str, Any] = {
            "event_id": event_id,
            "serial": serial,
            "issue_time": issue.get("time"),
            "origin_time": earthquake.get("originTime"),
            "hypocenter": hypocenter.get("name"),
            "magnitude": hypocenter.get("magnitude"),
            "depth_km": hypocenter.get("depth"),
            "latitude": hypocenter.get("latitude"),
            "longitude": hypocenter.get("longitude"),
            "max_scale_from": scale_from,
            "max_scale_to": scale_to,
            "area_filter": self.area,
            "areas": source_areas,
            "test": False,
            "recovered_after_reconnect": recovered,
        }

        # Every matching update refreshes sensor attributes and the active timer.
        self.last_warning = details
        self.warning_active = True
        self._notify()
        self._schedule_clear(AUTO_CLEAR_SECONDS)

        # Only NOW is the event considered alerted.
        # This is what guarantees "first report outside target, later report
        # inside target" still triggers exactly once.
        dedup_key = event_id or message_id or f"{issue.get('time')}:{serial}"

        if dedup_key in self._alerted_event_ids:
            return

        self._alerted_event_ids.add(dedup_key)
        if len(self._alerted_event_ids) > 200:
            self._alerted_event_ids.pop()

        _LOGGER.warning(
            "EEW ALERT: event=%s serial=%s target=%s recovered=%s",
            event_id,
            serial,
            self.area or "全国",
            recovered,
        )
        self.hass.bus.async_fire(EVENT_WARNING, details)

    def _schedule_clear(self, seconds: int) -> None:
        if self._clear_task and not self._clear_task.done():
            self._clear_task.cancel()

        self._clear_task = self.hass.async_create_background_task(
            self._async_clear_after(seconds),
            "P2P EEW auto clear",
        )

    async def _async_clear_after(self, seconds: int) -> None:
        try:
            await asyncio.sleep(seconds)
        except asyncio.CancelledError:
            return

        self.warning_active = False
        self._notify()

    async def async_test_warning(self) -> None:
        now = datetime.now(timezone.utc)
        event_id = f"TEST-{int(now.timestamp())}"

        details: dict[str, Any] = {
            "event_id": event_id,
            "serial": "TEST",
            "issue_time": now.isoformat(),
            "origin_time": now.isoformat(),
            "hypocenter": "テスト震源",
            "magnitude": 6.0,
            "depth_km": 30,
            "latitude": None,
            "longitude": None,
            "max_scale_from": 50,
            "max_scale_to": 55,
            "area_filter": self.area,
            "areas": [
                {
                    "pref": self.area or "テスト地域",
                    "name": self.area or "テスト地域",
                    "scaleFrom": 50,
                    "scaleTo": 55,
                }
            ],
            "test": True,
            "recovered_after_reconnect": False,
        }

        self.last_warning = details
        self.warning_active = True
        self._notify()
        self._schedule_clear(TEST_CLEAR_SECONDS)
        self.hass.bus.async_fire(EVENT_WARNING, details)
