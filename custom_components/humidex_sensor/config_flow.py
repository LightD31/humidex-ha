"""Config flow for Humidex Sensor integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, DEFAULT_NAME, ATTR_TEMPERATURE, ATTR_HUMIDITY, ATTR_PRESSURE

_LOGGER = logging.getLogger(__name__)


class HumidexConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Humidex Sensor."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate that entities exist and are of the correct type
                await self._validate_input(user_input)

                # Create a unique name for the entry if not specified
                title = user_input.get(CONF_NAME, DEFAULT_NAME)

                # Create the configuration entry
                return self.async_create_entry(
                    title=title,
                    data=user_input
                )
            except vol.Invalid:
                errors["base"] = "invalid_entity"
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", exc)
                errors["base"] = "unknown"

        # Form schema
        data_schema = vol.Schema({
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Required(ATTR_TEMPERATURE): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="temperature"
                )
            ),
            vol.Required(ATTR_HUMIDITY): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor", 
                    device_class="humidity"
                )
            ),
            vol.Optional(ATTR_PRESSURE): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="atmospheric_pressure"
                )
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    async def _validate_input(self, user_input: dict[str, Any]) -> None:
        """Validate the user input."""
        # Check that entities exist
        temp_entity = user_input[ATTR_TEMPERATURE]
        humidity_entity = user_input[ATTR_HUMIDITY]
        pressure_entity = user_input.get(ATTR_PRESSURE)

        temp_state = self.hass.states.get(temp_entity)
        humidity_state = self.hass.states.get(humidity_entity)

        if temp_state is None:
            raise vol.Invalid(f"Temperature entity {temp_entity} not found")
        if humidity_state is None:
            raise vol.Invalid(f"Humidity entity {humidity_entity} not found")

        # Check pressure entity if provided
        if pressure_entity:
            pressure_state = self.hass.states.get(pressure_entity)
            if pressure_state is None:
                raise vol.Invalid(f"Pressure entity {pressure_entity} not found")
            try:
                float(pressure_state.state)
            except (ValueError, TypeError):
                raise vol.Invalid(f"Pressure entity {pressure_entity} does not have a numeric state")

        # Check that values are numeric
        try:
            float(temp_state.state)
        except (ValueError, TypeError):
            raise vol.Invalid(f"Temperature entity {temp_entity} does not have a numeric state")

        try:
            float(humidity_state.state)
        except (ValueError, TypeError):
            raise vol.Invalid(f"Humidity entity {humidity_entity} does not have a numeric state")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Humidex Sensor."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate the new entities
                temp_entity = user_input[ATTR_TEMPERATURE]
                humidity_entity = user_input[ATTR_HUMIDITY]
                pressure_entity = user_input.get(ATTR_PRESSURE)

                temp_state = self.hass.states.get(temp_entity)
                humidity_state = self.hass.states.get(humidity_entity)

                if temp_state is None or humidity_state is None:
                    errors["base"] = "invalid_entity"
                elif pressure_entity and self.hass.states.get(pressure_entity) is None:
                    errors["base"] = "invalid_entity"
                else:
                    return self.async_create_entry(title="", data=user_input)

            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in options: %s", exc)
                errors["base"] = "unknown"

        # Schema with current values
        current_temp = self.config_entry.data.get(ATTR_TEMPERATURE, "")
        current_humidity = self.config_entry.data.get(ATTR_HUMIDITY, "")
        current_pressure = self.config_entry.data.get(ATTR_PRESSURE, "")

        data_schema = vol.Schema({
            vol.Required(ATTR_TEMPERATURE, default=current_temp): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="temperature"
                )
            ),
            vol.Required(ATTR_HUMIDITY, default=current_humidity): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="humidity"
                )
            ),
            vol.Optional(ATTR_PRESSURE, default=current_pressure): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="atmospheric_pressure"
                )
            ),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors
        )
