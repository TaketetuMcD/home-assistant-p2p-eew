from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from .const import CONF_AREA, DOMAIN


class P2PEEWConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            area = str(user_input.get(CONF_AREA, "")).strip()
            return self.async_create_entry(
                title="緊急地震速報",
                data={CONF_AREA: area},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_AREA, default=""): str,
                }
            ),
        )
