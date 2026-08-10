"""Config Flow für die REWE Lieferung Integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SLOW_SCAN_INTERVAL,
    CONF_WEBHOOK_ID,
    CONF_ZIP_CODE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLOW_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZIP_CODE): str,
    }
)


class ReweLieferungConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config Flow Handler."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                **user_input,
                CONF_WEBHOOK_ID: webhook.async_generate_id(),
            }
            return self.async_create_entry(title="REWE Lieferung", data=data)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return ReweLieferungOptionsFlow(entry)


class ReweLieferungOptionsFlow(OptionsFlow):
    """Optionen: Abfrageintervall anpassen."""

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.entry.options.get(
            CONF_SCAN_INTERVAL,
            self.entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_slow = self.entry.options.get(
            CONF_SLOW_SCAN_INTERVAL,
            self.entry.data.get(CONF_SLOW_SCAN_INTERVAL, DEFAULT_SLOW_SCAN_INTERVAL),
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)
                ),
                vol.Required(CONF_SLOW_SCAN_INTERVAL, default=current_slow): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
