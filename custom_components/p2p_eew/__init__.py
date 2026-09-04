from __future__ import annotations

import logging
from pathlib import Path
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .client import P2PEEWClient
from .const import (
    CONF_AREA,
    CONF_AREAS,
    CONF_MIN_SCALE,
    CONF_NOTIFY_INTENSITY_INCREASE,
    DEFAULT_MIN_SCALE,
    DEFAULT_NOTIFY_INTENSITY_INCREASE,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON]
BLUEPRINT_FILENAME = "eew_alarm.yaml"


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


async def _async_install_managed_blueprint(hass: HomeAssistant) -> None:
    """Install/update the bundled automation blueprint."""
    source = Path(__file__).parent / "blueprints" / BLUEPRINT_FILENAME
    destination = Path(
        hass.config.path(
            "blueprints",
            "automation",
            "p2p_eew",
            BLUEPRINT_FILENAME,
        )
    )
    try:
        await hass.async_add_executor_job(_copy_file, source, destination)
        _LOGGER.info("Installed EEW automation blueprint at %s", destination)
    except OSError as err:
        _LOGGER.error("Could not install EEW automation blueprint: %s", err)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a single-area version 1 entry to version 2 options."""
    if entry.version > 2:
        _LOGGER.error(
            "Cannot migrate P2P EEW entry from unsupported version %s",
            entry.version,
        )
        return False

    if entry.version == 1:
        old_area = str(entry.data.get(CONF_AREA, "")).strip()
        new_data = {
            key: value for key, value in entry.data.items() if key != CONF_AREA
        }
        new_data.update(
            {
                CONF_AREAS: [old_area] if old_area else [],
                CONF_MIN_SCALE: DEFAULT_MIN_SCALE,
                CONF_NOTIFY_INTENSITY_INCREASE: (
                    DEFAULT_NOTIFY_INTENSITY_INCREASE
                ),
            }
        )
        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            version=2,
        )
        _LOGGER.info("Migrated P2P EEW config entry to version 2")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await _async_install_managed_blueprint(hass)

    client = P2PEEWClient(hass, entry)
    entry.runtime_data = client

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_create_background_task(
        hass,
        client.async_run(),
        "P2P EEW WebSocket",
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client: P2PEEWClient = entry.runtime_data
    await client.async_stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
