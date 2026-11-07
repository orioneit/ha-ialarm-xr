"""Config flow for iAlarm-XR."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_PORT
from homeassistant.core import callback

from .api import IAlarmAuthError, IAlarmError, IAlarmXR
from .const import (
    CONF_DEVICE_ID,
    CONF_PIN,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def _validate(device_id: str, password: str, host: str, port: int) -> str | None:
    """Return an error key, or None if the credentials work."""
    try:
        await IAlarmXR(device_id, password, host, port).validate()
    except IAlarmAuthError:
        return "invalid_auth"
    except IAlarmError:
        return "cannot_connect"
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Unexpected error")
        return "unknown"
    return None


class IAlarmConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID].strip()
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            error = await _validate(device_id, user_input[CONF_PASSWORD], host, port)
            if error is None:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or f"iAlarm-XR {device_id}",
                    data={
                        CONF_DEVICE_ID: device_id,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_HOST: host,
                        CONF_PORT: port,
                    },
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default="iAlarm-XR"): str,
                    vol.Required(CONF_DEVICE_ID): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=65535)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            error = await _validate(
                entry.data[CONF_DEVICE_ID],
                user_input[CONF_PASSWORD],
                entry.data[CONF_HOST],
                entry.data[CONF_PORT],
            )
            if error is None:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return IAlarmOptionsFlow()


class IAlarmOptionsFlow(OptionsFlow):
    """Options: polling interval and optional disarm PIN."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=3600)),
                    vol.Optional(
                        CONF_PIN,
                        description={"suggested_value": options.get(CONF_PIN, "")},
                    ): vol.All(str, vol.Match(r"^\d{0,8}$")),
                }
            ),
        )
