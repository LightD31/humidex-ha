"""Humidex sensor platform for Home Assistant."""
from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import StateType
from homeassistant.util.unit_conversion import TemperatureConverter
from homeassistant.helpers import translation

from .const import DOMAIN, DEFAULT_NAME, DEFAULT_ICON, ATTR_TEMPERATURE, ATTR_HUMIDITY, ATTR_PRESSURE

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0  # Event-driven updates


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Humidex sensor from config entry."""
    _LOGGER.debug("Setting up Humidex sensor from config entry")

    # Get configuration data directly from config_entry
    config = config_entry.data

    name = config.get(CONF_NAME, DEFAULT_NAME)
    temp_entity = config[ATTR_TEMPERATURE]
    humidity_entity = config[ATTR_HUMIDITY]
    pressure_entity = config.get(ATTR_PRESSURE)

    # Create the sensor entity
    humidex_sensor = HumidexSensor(
        hass=hass,
        config_entry=config_entry,
        name=name,
        temp_entity_id=temp_entity,
        humidity_entity_id=humidity_entity,
        pressure_entity_id=pressure_entity
    )

    async_add_entities([humidex_sensor], True)


class HumidexSensor(SensorEntity):
    """Representation of a Humidex sensor."""

    _attr_icon = DEFAULT_ICON
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        name: str,
        temp_entity_id: str,
        humidity_entity_id: str,
        pressure_entity_id: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._config_entry = config_entry
        self._temp_entity_id = temp_entity_id
        self._humidity_entity_id = humidity_entity_id
        self._pressure_entity_id = pressure_entity_id

        # Entity attributes
        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_humidex"
        self._attr_native_value: float | None = None
        
        # Translation cache
        self._translations: dict[str, Any] | None = None

        # Device information
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": name,
            "manufacturer": "Humidex Sensor",
            "model": "Virtual Sensor",
            "sw_version": "1.0.0",
        }

        _LOGGER.debug(
            "Initialized Humidex sensor '%s' with temp=%s, humidity=%s, pressure=%s",
            name, temp_entity_id, humidity_entity_id, pressure_entity_id
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        attrs = {
            "temperature_entity": self._temp_entity_id,
            "humidity_entity": self._humidity_entity_id,
        }
        
        if self._pressure_entity_id:
            attrs["pressure_entity"] = self._pressure_entity_id
            attrs["calculation_method"] = "enhanced"
        else:
            attrs["calculation_method"] = "standard"
        
        # Add comfort information if a value is available
        if self._attr_native_value is not None:
            attrs["comfort_level"] = self._get_comfort_level(self._attr_native_value)
            # For synchronous property, use the cached comfort description
            attrs["comfort_description"] = self._get_comfort_description_sync(self._attr_native_value)
        
        return attrs

    def _get_comfort_description_sync(self, humidex: float) -> str:
        """Get comfort description synchronously using cached translations."""
        comfort_level = self._get_comfort_level(humidex)
        
        # Try to get translated description from cache
        try:
            if self._translations:
                translation_key = f"component.{DOMAIN}.entity.sensor.humidex.state_attributes.comfort_description.{comfort_level}"
                translated = self._translations.get(translation_key)
                if translated:
                    return translated
        except Exception:
            pass
        
        # Fallback to English descriptions
        fallback_descriptions = {
            "cold": "Cold",
            "comfortable": "Comfortable",
            "slightly_uncomfortable": "Slightly uncomfortable",
            "very_uncomfortable": "Very uncomfortable",
            "dangerous": "Dangerous"
        }
        return fallback_descriptions.get(comfort_level, "Unknown")

    async def _get_translations(self) -> dict[str, Any]:
        """Get translations for the current language."""
        if self._translations is None:
            self._translations = await translation.async_get_translations(
                self.hass, self.hass.config.language, "entity", {DOMAIN}
            )
        return self._translations

    def _get_comfort_level(self, humidex: float) -> str:
        """Get comfort level based on humidex value."""
        if humidex < 20:
            return "cold"
        elif humidex <= 29:
            return "comfortable"
        elif humidex <= 39:
            return "slightly_uncomfortable"
        elif humidex <= 45:
            return "very_uncomfortable"
        else:
            return "dangerous"

    def _calculate_dew_point(self, temperature: float, humidity: float) -> float:
        """Calculate dew point using simple approximation."""
        return temperature - ((100 - humidity) / 5)

    def _calculate_vapor_pressure_standard(self, temperature: float, humidity: float) -> float:
        """Calculate vapor pressure using standard method (dew point based)."""
        # Calculate dew point
        dew_point = self._calculate_dew_point(temperature, humidity)
        
        # Official Environment Canada formula using dew point
        # e = 6.11 * exp[5417.7530 * ((1/273.15) - (1/(T_dew + 273.15)))]
        exponent = 5417.7530 * ((1/273.15) - (1/(dew_point + 273.15)))
        vapor_pressure = 6.11 * math.exp(exponent)
        
        return vapor_pressure

    def _calculate_vapor_pressure_enhanced(self, temperature: float, humidity: float, pressure: float) -> float:
        """Calculate vapor pressure using enhanced method with atmospheric pressure."""
        # Saturated vapor pressure using Magnus-Tetens formula
        es = 6.1078 * math.exp((17.27 * temperature) / (temperature + 237.3))
        
        # Actual vapor pressure
        e = (humidity / 100.0) * es
        
        # Correction for atmospheric pressure
        e_corrected = e * (pressure / 1013.25)
        
        return e_corrected

    def _convert_temperature_to_celsius(self, temperature: float, unit: str) -> float:
        """Convert temperature to Celsius if needed."""
        if unit == UnitOfTemperature.FAHRENHEIT:
            return TemperatureConverter.convert(
                temperature, UnitOfTemperature.FAHRENHEIT, UnitOfTemperature.CELSIUS
            )
        return temperature

    def _validate_sensor_values(self, temperature: float, humidity: float, pressure: float | None = None) -> bool:
        """Validate sensor values are within reasonable ranges."""
        # Temperature range: -50°C to +70°C
        if not -50 <= temperature <= 70:
            _LOGGER.warning(
                "Temperature %.1f°C is outside valid range (-50°C to +70°C)", 
                temperature
            )
            return False
        
        # Humidity range: 0% to 100%
        if not 0 <= humidity <= 100:
            _LOGGER.warning(
                "Humidity %.1f%% is outside valid range (0%% to 100%%)", 
                humidity
            )
            return False
        
        # Pressure range: 800 to 1200 hPa (if provided)
        if pressure is not None and not 800 <= pressure <= 1200:
            _LOGGER.warning(
                "Pressure %.1f hPa is outside valid range (800 to 1200 hPa)", 
                pressure
            )
            return False
        
        return True

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        # Load translations
        await self._get_translations()

        # Subscribe to state changes of source entities
        entities_to_track = [self._temp_entity_id, self._humidity_entity_id]
        if self._pressure_entity_id:
            entities_to_track.append(self._pressure_entity_id)
            
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                entities_to_track,
                self._async_sensor_state_listener,
            )
        )

        # Calculate initial value
        await self._async_update_humidex()

    @callback
    def _async_sensor_state_listener(self, event) -> None:
        """Handle state changes of source sensors."""
        _LOGGER.debug("Source sensor state changed: %s", event.data.get("entity_id"))
        self.hass.async_create_task(self._async_update_humidex())

    async def _async_update_humidex(self) -> None:
        """Update the humidex value."""
        try:
            # Get states of source sensors
            temp_state = self.hass.states.get(self._temp_entity_id)
            humidity_state = self.hass.states.get(self._humidity_entity_id)
            pressure_state = None
            if self._pressure_entity_id:
                pressure_state = self.hass.states.get(self._pressure_entity_id)

            if temp_state is None:
                _LOGGER.warning("Temperature entity '%s' not found", self._temp_entity_id)
                self._attr_native_value = None
                self._attr_available = False
                self.async_write_ha_state()
                return

            if humidity_state is None:
                _LOGGER.warning("Humidity entity '%s' not found", self._humidity_entity_id)
                self._attr_native_value = None
                self._attr_available = False
                self.async_write_ha_state()
                return

            # Check that states are not unavailable or unknown
            if temp_state.state in ("unavailable", "unknown"):
                _LOGGER.warning("Temperature entity '%s' is %s", self._temp_entity_id, temp_state.state)
                self._attr_native_value = None
                self._attr_available = False
                self.async_write_ha_state()
                return

            if humidity_state.state in ("unavailable", "unknown"):
                _LOGGER.warning("Humidity entity '%s' is %s", self._humidity_entity_id, humidity_state.state)
                self._attr_native_value = None
                self._attr_available = False
                self.async_write_ha_state()
                return

            # Check pressure state if configured
            if self._pressure_entity_id and pressure_state and pressure_state.state in ("unavailable", "unknown"):
                _LOGGER.warning("Pressure entity '%s' is %s", self._pressure_entity_id, pressure_state.state)
                # Don't fail, just use standard calculation
                pressure_state = None

            # Check that values are numeric
            try:
                temperature_raw = float(temp_state.state)
                humidity = float(humidity_state.state)
                pressure = None
                if pressure_state and pressure_state.state not in ("unavailable", "unknown"):
                    pressure = float(pressure_state.state)
            except (ValueError, TypeError) as err:
                pressure_str = "N/A" if pressure_state is None else pressure_state.state
                _LOGGER.error("Invalid numeric values: temp=%s, humidity=%s, pressure=%s (%s)", 
                             temp_state.state, humidity_state.state, pressure_str, err)
                self._attr_native_value = None
                self._attr_available = False
                self.async_write_ha_state()
                return

            # Convert temperature to Celsius if necessary
            temp_unit = temp_state.attributes.get("unit_of_measurement", UnitOfTemperature.CELSIUS)
            temperature = self._convert_temperature_to_celsius(temperature_raw, temp_unit)

            # Validate value ranges
            if not self._validate_sensor_values(temperature, humidity, pressure):
                self._attr_native_value = None
                self._attr_available = False
                self.async_write_ha_state()
                return

            # Calculate humidex using appropriate method
            if pressure is not None:
                # Enhanced calculation with atmospheric pressure
                vapor_pressure = self._calculate_vapor_pressure_enhanced(temperature, humidity, pressure)
                calculation_method = "enhanced"
            else:
                # Standard calculation based on dew point
                vapor_pressure = self._calculate_vapor_pressure_standard(temperature, humidity)
                calculation_method = "standard"

            # Final Humidex calculation: Humidex = T + 0.5555 * (e - 10)
            humidex = temperature + 0.5555 * (vapor_pressure - 10)

            # Round to 1 decimal place
            self._attr_native_value = round(humidex, 1)
            self._attr_available = True

            _LOGGER.debug(
                "Calculated humidex: %.1f°C using %s method (temp=%.1f°C, humidity=%.1f%%, pressure=%s)",
                self._attr_native_value, calculation_method, temperature, humidity, 
                f"{pressure:.1f} hPa" if pressure else "N/A"
            )

        except Exception as err:
            _LOGGER.error("Error calculating humidex: %s", err)
            self._attr_native_value = None
            self._attr_available = False

        # Update state
        self.async_write_ha_state()
