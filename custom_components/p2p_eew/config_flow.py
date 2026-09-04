from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_AREAS,
    CONF_MIN_SCALE,
    CONF_NOTIFY_INTENSITY_INCREASE,
    DEFAULT_MIN_SCALE,
    DEFAULT_NOTIFY_INTENSITY_INCREASE,
    DOMAIN,
)
from .matching import PREFECTURE_FORECAST_AREAS

MINIMUM_SCALE_OPTIONS = (
    SelectOptionDict(value="-1", label="指定なし / Any"),
    SelectOptionDict(value="40", label="震度4 / 4"),
    SelectOptionDict(value="45", label="震度5弱 / 5 lower"),
    SelectOptionDict(value="50", label="震度5強 / 5 upper"),
    SelectOptionDict(value="55", label="震度6弱 / 6 lower"),
    SelectOptionDict(value="60", label="震度6強 / 6 upper"),
    SelectOptionDict(value="70", label="震度7 / 7"),
)


def _defaults(entry: config_entries.ConfigEntry | None = None) -> dict[str, Any]:
    if entry is None:
        return {
            CONF_AREAS: [],
            CONF_MIN_SCALE: DEFAULT_MIN_SCALE,
            CONF_NOTIFY_INTENSITY_INCREASE: DEFAULT_NOTIFY_INTENSITY_INCREASE,
        }
    return {**entry.data, **entry.options}


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    selected = defaults.get(CONF_AREAS, [])
    if isinstance(selected, str):
        selected = [selected] if selected.strip() else []

    return vol.Schema(
        {
            vol.Optional(CONF_AREAS, default=selected): SelectSelector(
                SelectSelectorConfig(
                    options=list(PREFECTURE_FORECAST_AREAS),
                    multiple=True,
                    custom_value=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_MIN_SCALE,
                default=str(defaults.get(CONF_MIN_SCALE, DEFAULT_MIN_SCALE)),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=list(MINIMUM_SCALE_OPTIONS),
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_NOTIFY_INTENSITY_INCREASE,
                default=bool(
                    defaults.get(
                        CONF_NOTIFY_INTENSITY_INCREASE,
                        DEFAULT_NOTIFY_INTENSITY_INCREASE,
                    )
                ),
            ): BooleanSelector(BooleanSelectorConfig()),
        }
    )


def _clean_input(user_input: dict[str, Any]) -> dict[str, Any]:
    raw_areas = user_input.get(CONF_AREAS, [])
    if isinstance(raw_areas, str):
        raw_areas = [raw_areas]
    areas = list(
        dict.fromkeys(
            str(area).strip() for area in raw_areas if str(area).strip()
        )
    )

    return {
        CONF_AREAS: areas,
        CONF_MIN_SCALE: int(user_input.get(CONF_MIN_SCALE, DEFAULT_MIN_SCALE)),
        CONF_NOTIFY_INTENSITY_INCREASE: bool(
            user_input.get(
                CONF_NOTIFY_INTENSITY_INCREASE,
                DEFAULT_NOTIFY_INTENSITY_INCREASE,
            )
        ),
    }


class P2PEEWConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="緊急地震速報",
                data=_clean_input(user_input),
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(_defaults()),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return P2PEEWOptionsFlow()


class P2PEEWOptionsFlow(config_entries.OptionsFlowWithReload):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=_clean_input(user_input))

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(_defaults(self.config_entry)),
        )
