"""Config flow for TiMini Print."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .client import TiminiPrintError, scan
from .const import DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="TiMini Print"): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


async def _test_connection(hass, host: str, port: int) -> None:
    """Confirm the add-on is reachable by asking it to scan for
    printers. Unlike the separate Cat Printer integration, this does
    NOT trigger a physical test print - TiMini-Print's --scan is a
    read-only operation, so setup never wastes paper.
    """
    await hass.async_add_executor_job(scan, host, port)


class TiminiPrintConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TiMini Print."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()

            try:
                await _test_connection(
                    self.hass, user_input[CONF_HOST], user_input[CONF_PORT]
                )
            except TiminiPrintError as err:
                _LOGGER.warning("TiMini Print connection test failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
