"""Config flow for WasherCycle."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import (
    CONF_DOOR_SENSOR,
    CONF_ENERGY_SENSOR,
    CONF_MOVEMENT_SENSOR,
    CONF_PLUG_SWITCH,
    CONF_POWER_SENSOR,
    DEFAULT_DEVICE_NAME,
    DEFAULT_DOOR_SENSOR,
    DEFAULT_ENERGY_SENSOR,
    DEFAULT_LEGACY_STATUS_MIRROR,
    DEFAULT_MOVEMENT_SENSOR,
    DEFAULT_PLUG_SWITCH,
    DEFAULT_POWER_SENSOR,
    DEFAULT_REWASH_DELAY_MINUTES,
    DEFAULT_SHADOW_MODE,
    DOMAIN,
    OPT_ADVANCED_DIAGNOSTICS,
    OPT_LEGACY_STATUS_MIRROR,
    OPT_REWASH_DELAY_MINUTES,
    OPT_SHADOW_MODE,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_POWER_SENSOR, default=DEFAULT_POWER_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="sensor", device_class="power")
        ),
        vol.Optional(CONF_ENERGY_SENSOR, default=DEFAULT_ENERGY_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="sensor", device_class="energy")
        ),
        vol.Required(CONF_DOOR_SENSOR, default=DEFAULT_DOOR_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="binary_sensor", device_class="door")
        ),
        vol.Optional(CONF_MOVEMENT_SENSOR, default=DEFAULT_MOVEMENT_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="binary_sensor", device_class="moving")
        ),
        vol.Optional(CONF_PLUG_SWITCH, default=DEFAULT_PLUG_SWITCH): EntitySelector(
            EntitySelectorConfig(domain="switch")
        ),
    }
)


def _default_options() -> dict[str, Any]:
    return {
        OPT_SHADOW_MODE: DEFAULT_SHADOW_MODE,
        OPT_LEGACY_STATUS_MIRROR: DEFAULT_LEGACY_STATUS_MIRROR,
        OPT_REWASH_DELAY_MINUTES: DEFAULT_REWASH_DELAY_MINUTES,
        OPT_ADVANCED_DIAGNOSTICS: False,
    }


class WasherCycleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle WasherCycle config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle initial setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            power_sensor = user_input[CONF_POWER_SENSOR]
            await self.async_set_unique_id(power_sensor)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=DEFAULT_DEVICE_NAME,
                data=user_input,
                options=_default_options(),
            )

        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> WasherCycleOptionsFlow:
        """Get options flow."""
        return WasherCycleOptionsFlow(config_entry)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle reconfiguration."""
        if user_input is not None:
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data=user_input,
            )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                USER_SCHEMA, self._get_reconfigure_entry().data
            ),
        )


class WasherCycleOptionsFlow(OptionsFlow):
    """Handle WasherCycle options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            errors = self._validate_options(user_input)
            if errors:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._options_schema(),
                    errors=errors,
                )
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                self._options_schema(),
                {**_default_options(), **self.config_entry.options},
            ),
        )

    def _options_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Optional(OPT_SHADOW_MODE): bool,
                vol.Optional(OPT_LEGACY_STATUS_MIRROR): bool,
                vol.Optional(OPT_REWASH_DELAY_MINUTES): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=1440)
                ),
                vol.Optional(OPT_ADVANCED_DIAGNOSTICS): bool,
            }
        )

    def _validate_options(self, options: dict[str, Any]) -> dict[str, str]:
        return {}
