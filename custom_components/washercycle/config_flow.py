"""Config flow for WasherCycle."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_DOOR_BATTERY_LOW_SENSOR,
    CONF_DOOR_BATTERY_SENSOR,
    CONF_DOOR_LQI_SENSOR,
    CONF_DOOR_SENSOR,
    CONF_ENERGY_SENSOR,
    CONF_MOVEMENT_SENSOR,
    CONF_PLUG_LQI_SENSOR,
    CONF_PLUG_SWITCH,
    CONF_POWER_SENSOR,
    CONF_TEMPERATURE_SENSOR,
    DEFAULT_ANNOUNCEMENT_RETRY_COUNT,
    DEFAULT_AUTO_INCLUDE_TRAINING_RUNS,
    DEFAULT_COMPLETED_HISTORY_RETENTION,
    DEFAULT_COMPLETION_ANNOUNCEMENTS_ENABLED,
    DEFAULT_COMPLETION_MESSAGE,
    DEFAULT_COMPLETION_SPEAKERS,
    DEFAULT_DEVICE_NAME,
    DEFAULT_DOOR_BATTERY_LOW_SENSOR,
    DEFAULT_DOOR_BATTERY_SENSOR,
    DEFAULT_DOOR_CORRELATION_SECONDS,
    DEFAULT_DOOR_LQI_SENSOR,
    DEFAULT_DOOR_SENSOR,
    DEFAULT_DOOR_SUPPRESSION_WINDOW_SECONDS,
    DEFAULT_EARLY_COMPLETION_ENABLED,
    DEFAULT_EARLY_COMPLETION_MIN_SCORE,
    DEFAULT_END_SIGNATURE_POST_SECONDS,
    DEFAULT_END_SIGNATURE_PRE_SECONDS,
    DEFAULT_ENERGY_SENSOR,
    DEFAULT_FALLBACK_COMPLETION_SECONDS,
    DEFAULT_MATCHER_MARGIN,
    DEFAULT_MAX_STALE_SECONDS,
    DEFAULT_MIN_RUNS_RECOGNITION,
    DEFAULT_MIN_RUNS_ROBUST,
    DEFAULT_MOVEMENT_ENABLED,
    DEFAULT_MOVEMENT_SENSOR,
    DEFAULT_PLUG_LQI_SENSOR,
    DEFAULT_PLUG_SWITCH,
    DEFAULT_POWER_SENSOR,
    DEFAULT_QUIET_HOURS_POLICY,
    DEFAULT_RAW_RUN_RETENTION,
    DEFAULT_RESAMPLE_INTERVAL_SECONDS,
    DEFAULT_REWASH_ANNOUNCEMENTS_ENABLED,
    DEFAULT_REWASH_DELAY_MINUTES,
    DEFAULT_REWASH_MESSAGE,
    DEFAULT_REWASH_SPEAKERS,
    DEFAULT_SHADOW_MODE,
    DEFAULT_STANDBY_POWER_W,
    DEFAULT_START_MIN_ENERGY_WH,
    DEFAULT_START_POWER_W,
    DEFAULT_START_SUSTAIN_SECONDS,
    DEFAULT_SUPPRESS_IF_DOOR_OPEN,
    DEFAULT_TARGET_LATENCY_SECONDS,
    DEFAULT_TEMPERATURE_SENSOR,
    DEFAULT_TTS_ENTITY,
    DEFAULT_TTS_MODE,
    DOMAIN,
    OPT_ANNOUNCEMENT_RETRY_COUNT,
    OPT_AUTO_INCLUDE_TRAINING_RUNS,
    OPT_COMPLETED_HISTORY_RETENTION,
    OPT_COMPLETION_ANNOUNCEMENTS_ENABLED,
    OPT_COMPLETION_MESSAGE,
    OPT_COMPLETION_SPEAKERS,
    OPT_DOOR_CORRELATION_SECONDS,
    OPT_DOOR_SUPPRESSION_WINDOW_SECONDS,
    OPT_EARLY_COMPLETION_ENABLED,
    OPT_EARLY_COMPLETION_MIN_SCORE,
    OPT_END_SIGNATURE_POST_SECONDS,
    OPT_END_SIGNATURE_PRE_SECONDS,
    OPT_FALLBACK_COMPLETION_SECONDS,
    OPT_LEGACY_STATUS_MIRROR,
    OPT_MATCHER_MARGIN,
    OPT_MAX_STALE_SECONDS,
    OPT_MIN_RUNS_RECOGNITION,
    OPT_MIN_RUNS_ROBUST,
    OPT_MOVEMENT_ENABLED,
    OPT_QUIET_HOURS_END,
    OPT_QUIET_HOURS_POLICY,
    OPT_QUIET_HOURS_START,
    OPT_RAW_RUN_RETENTION,
    OPT_RESAMPLE_INTERVAL_SECONDS,
    OPT_REWASH_ANNOUNCEMENTS_ENABLED,
    OPT_REWASH_DELAY_MINUTES,
    OPT_REWASH_MESSAGE,
    OPT_REWASH_SPEAKERS,
    OPT_SHADOW_MODE,
    OPT_STANDBY_POWER_W,
    OPT_START_MIN_ENERGY_WH,
    OPT_START_POWER_W,
    OPT_START_SUSTAIN_SECONDS,
    OPT_SUPPRESS_IF_DOOR_OPEN,
    OPT_TARGET_LATENCY_SECONDS,
    OPT_TTS_ENTITY,
    OPT_TTS_MODE,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_POWER_SENSOR, default=DEFAULT_POWER_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="sensor", device_class="power")
        ),
        vol.Required(CONF_ENERGY_SENSOR, default=DEFAULT_ENERGY_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="sensor", device_class="energy")
        ),
        vol.Required(CONF_PLUG_SWITCH, default=DEFAULT_PLUG_SWITCH): EntitySelector(
            EntitySelectorConfig(domain="switch")
        ),
        vol.Required(CONF_DOOR_SENSOR, default=DEFAULT_DOOR_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="binary_sensor", device_class="door")
        ),
        vol.Required(CONF_MOVEMENT_SENSOR, default=DEFAULT_MOVEMENT_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="binary_sensor", device_class="moving")
        ),
        vol.Optional(CONF_TEMPERATURE_SENSOR, default=DEFAULT_TEMPERATURE_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="sensor", device_class="temperature")
        ),
        vol.Optional(CONF_PLUG_LQI_SENSOR, default=DEFAULT_PLUG_LQI_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_DOOR_LQI_SENSOR, default=DEFAULT_DOOR_LQI_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_DOOR_BATTERY_SENSOR, default=DEFAULT_DOOR_BATTERY_SENSOR): EntitySelector(
            EntitySelectorConfig(domain="sensor", device_class="battery")
        ),
        vol.Optional(
            CONF_DOOR_BATTERY_LOW_SENSOR, default=DEFAULT_DOOR_BATTERY_LOW_SENSOR
        ): EntitySelector(EntitySelectorConfig(domain="binary_sensor")),
    }
)


def _default_options() -> dict[str, Any]:
    return {
        OPT_START_POWER_W: DEFAULT_START_POWER_W,
        OPT_START_SUSTAIN_SECONDS: DEFAULT_START_SUSTAIN_SECONDS,
        OPT_START_MIN_ENERGY_WH: DEFAULT_START_MIN_ENERGY_WH,
        OPT_STANDBY_POWER_W: DEFAULT_STANDBY_POWER_W,
        OPT_FALLBACK_COMPLETION_SECONDS: DEFAULT_FALLBACK_COMPLETION_SECONDS,
        OPT_EARLY_COMPLETION_ENABLED: DEFAULT_EARLY_COMPLETION_ENABLED,
        OPT_EARLY_COMPLETION_MIN_SCORE: DEFAULT_EARLY_COMPLETION_MIN_SCORE,
        OPT_DOOR_CORRELATION_SECONDS: DEFAULT_DOOR_CORRELATION_SECONDS,
        OPT_MOVEMENT_ENABLED: DEFAULT_MOVEMENT_ENABLED,
        OPT_TARGET_LATENCY_SECONDS: DEFAULT_TARGET_LATENCY_SECONDS,
        OPT_MAX_STALE_SECONDS: DEFAULT_MAX_STALE_SECONDS,
        OPT_SHADOW_MODE: DEFAULT_SHADOW_MODE,
        OPT_LEGACY_STATUS_MIRROR: False,
        OPT_MIN_RUNS_RECOGNITION: DEFAULT_MIN_RUNS_RECOGNITION,
        OPT_MIN_RUNS_ROBUST: DEFAULT_MIN_RUNS_ROBUST,
        OPT_RESAMPLE_INTERVAL_SECONDS: DEFAULT_RESAMPLE_INTERVAL_SECONDS,
        OPT_RAW_RUN_RETENTION: DEFAULT_RAW_RUN_RETENTION,
        OPT_COMPLETED_HISTORY_RETENTION: DEFAULT_COMPLETED_HISTORY_RETENTION,
        OPT_END_SIGNATURE_PRE_SECONDS: DEFAULT_END_SIGNATURE_PRE_SECONDS,
        OPT_END_SIGNATURE_POST_SECONDS: DEFAULT_END_SIGNATURE_POST_SECONDS,
        OPT_AUTO_INCLUDE_TRAINING_RUNS: DEFAULT_AUTO_INCLUDE_TRAINING_RUNS,
        OPT_MATCHER_MARGIN: DEFAULT_MATCHER_MARGIN,
        OPT_COMPLETION_ANNOUNCEMENTS_ENABLED: DEFAULT_COMPLETION_ANNOUNCEMENTS_ENABLED,
        OPT_REWASH_ANNOUNCEMENTS_ENABLED: DEFAULT_REWASH_ANNOUNCEMENTS_ENABLED,
        OPT_COMPLETION_SPEAKERS: DEFAULT_COMPLETION_SPEAKERS,
        OPT_REWASH_SPEAKERS: DEFAULT_REWASH_SPEAKERS,
        OPT_REWASH_DELAY_MINUTES: DEFAULT_REWASH_DELAY_MINUTES,
        OPT_COMPLETION_MESSAGE: DEFAULT_COMPLETION_MESSAGE,
        OPT_REWASH_MESSAGE: DEFAULT_REWASH_MESSAGE,
        OPT_SUPPRESS_IF_DOOR_OPEN: DEFAULT_SUPPRESS_IF_DOOR_OPEN,
        OPT_DOOR_SUPPRESSION_WINDOW_SECONDS: DEFAULT_DOOR_SUPPRESSION_WINDOW_SECONDS,
        OPT_TTS_ENTITY: DEFAULT_TTS_ENTITY,
        OPT_TTS_MODE: DEFAULT_TTS_MODE,
        OPT_QUIET_HOURS_START: None,
        OPT_QUIET_HOURS_END: None,
        OPT_QUIET_HOURS_POLICY: DEFAULT_QUIET_HOURS_POLICY,
        OPT_ANNOUNCEMENT_RETRY_COUNT: DEFAULT_ANNOUNCEMENT_RETRY_COUNT,
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

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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
                vol.Optional(OPT_START_POWER_W): vol.Coerce(float),
                vol.Optional(OPT_STANDBY_POWER_W): vol.Coerce(float),
                vol.Optional(OPT_START_SUSTAIN_SECONDS): vol.Coerce(int),
                vol.Optional(OPT_FALLBACK_COMPLETION_SECONDS): vol.Coerce(int),
                vol.Optional(OPT_EARLY_COMPLETION_ENABLED): bool,
                vol.Optional(OPT_EARLY_COMPLETION_MIN_SCORE): vol.Coerce(float),
                vol.Optional(OPT_DOOR_CORRELATION_SECONDS): vol.Coerce(int),
                vol.Optional(OPT_MOVEMENT_ENABLED): bool,
                vol.Optional(OPT_MIN_RUNS_RECOGNITION): vol.All(vol.Coerce(int), vol.Range(min=1, max=20)),
                vol.Optional(OPT_MIN_RUNS_ROBUST): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
                vol.Optional(OPT_COMPLETION_ANNOUNCEMENTS_ENABLED): bool,
                vol.Optional(OPT_REWASH_ANNOUNCEMENTS_ENABLED): bool,
                vol.Optional(OPT_REWASH_DELAY_MINUTES): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
                vol.Optional(OPT_COMPLETION_MESSAGE): TextSelector(TextSelectorConfig()),
                vol.Optional(OPT_REWASH_MESSAGE): TextSelector(TextSelectorConfig()),
                vol.Optional(OPT_TTS_ENTITY): TextSelector(TextSelectorConfig()),
                vol.Optional(OPT_TTS_MODE): SelectSelector(
                    SelectSelectorConfig(
                        options=["speak", "cloud_say"],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

    def _validate_options(self, options: dict[str, Any]) -> dict[str, str]:
        errors: dict[str, str] = {}
        start = options.get(OPT_START_POWER_W, DEFAULT_START_POWER_W)
        standby = options.get(OPT_STANDBY_POWER_W, DEFAULT_STANDBY_POWER_W)
        if start <= standby:
            errors["base"] = "start_power_must_exceed_standby"
        fallback = options.get(OPT_FALLBACK_COMPLETION_SECONDS, DEFAULT_FALLBACK_COMPLETION_SECONDS)
        if fallback < 120:
            errors["base"] = "fallback_too_short"
        return errors
