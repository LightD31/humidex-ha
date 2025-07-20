# Humidex Sensor for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/LightD31/humidex-ha?style=for-the-badge)](https://github.com/LightD31/humidex-ha/releases)
[![GitHub](https://img.shields.io/github/license/LightD31/humidex-ha?style=for-the-badge)](LICENSE)

A Home Assistant integration that calculates the Humidex index based on your existing temperature and humidity sensors.

## What is Humidex?

Humidex (humidity index) is a measure used by Canadian meteorologists to describe how hot and humid air feels to the human body. It combines air temperature and relative humidity into a single number to represent the perceived temperature.

### Humidex Comfort Scale

- **20-29°C**: Comfortable
- **30-39°C**: Slightly uncomfortable
- **40-45°C**: Very uncomfortable, avoid physical exertion
- **46°C and above**: Dangerous, heat stroke imminent

## Features

- ✅ Real-time Humidex index calculation
- ✅ Automatic updates when temperature/humidity changes
- ✅ Support for Celsius and Fahrenheit sensors
- ✅ Optional atmospheric pressure sensor for enhanced precision
- ✅ Dual calculation methods (standard dew point-based and enhanced pressure-corrected)
- ✅ Graphical configuration interface (Config Flow)
- ✅ Multilingual support (French/English)
- ✅ HACS compatible
- ✅ Robust input data validation

## Installation

### Via HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right
4. Select "Custom repositories"
5. Add `https://github.com/LightD31/humidex-ha` as an integration
6. Search for "Humidex Sensor" and install it
7. Restart Home Assistant

### Manual Installation

1. Download the files from GitHub
2. Copy the `custom_components/humidex_sensor` folder to your `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

### Via User Interface

1. Go to **Configuration** > **Integrations**
2. Click **+ Add Integration**
3. Search for "Humidex Sensor"
4. Follow the configuration wizard:
   - **Name**: Custom name for your sensor (optional)
   - **Temperature entity**: Select your temperature sensor
   - **Humidity entity**: Select your humidity sensor
   - **Pressure entity**: Select your atmospheric pressure sensor (optional, for enhanced precision)

### Supported Sensors

- **Temperature**: Any sensor with device_class "temperature" (°C or °F)
- **Humidity**: Any sensor with device_class "humidity" (%)
- **Pressure**: Any sensor with device_class "atmospheric_pressure" (hPa/mbar) - Optional for enhanced precision

## Usage

Once configured, the Humidex sensor will appear in your entities with:

- **State**: Humidex index value in °C
- **Attributes**:
  - `temperature_entity`: Source temperature entity
  - `humidity_entity`: Source humidity entity
  - `pressure_entity`: Source pressure entity (if configured)
  - `calculation_method`: Method used (standard or enhanced)
  - `comfort_level`: Comfort level (cold, comfortable, slightly_uncomfortable, very_uncomfortable, dangerous)
  - `comfort_description`: Comfort description in French

### Lovelace Example

```yaml
type: gauge
entity: sensor.humidex
name: Humidex Index
min: 15
max: 50
severity:
  green: 29
  yellow: 39
  red: 45
```

## Calculation Formula

The integration uses the official Environment Canada formula based on dew point temperature:

$$T_{dew} = T - \frac{100 - RH}{5}$$

$$e = 6.11 \times \exp\left[5417.7530 \times \left(\frac{1}{273.15} - \frac{1}{T_{dew} + 273.15}\right)\right]$$

$$\text{Humidex} = T + 0.5555 \times (e - 10)$$

### Enhanced Precision with Atmospheric Pressure (Optional)

When a pressure sensor is available, the integration can use a more precise calculation:

$$e_{s} = 6.1078 \times \exp\left(\frac{17.27 \times T}{T + 237.3}\right)$$

$$e = \frac{RH}{100} \times e_{s} \times \frac{P}{1013.25}$$

Where:

- **T** = temperature in °C
- **RH** = relative humidity in %
- **T_dew** = dew point temperature in °C
- **e** = water vapor pressure in hPa
- **P** = atmospheric pressure in hPa (optional)
- **e_s** = saturated vapor pressure

## Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/LightD31/humidex-ha/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/LightD31/humidex-ha/discussions)
- 📖 **Documentation**: [Wiki](https://github.com/LightD31/humidex-ha/wiki)

## Contributing

Contributions are welcome! Make a pull request or open an issue to discuss improvements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Acknowledgments

- Humidex formula based on Environment and Climate Change Canada standards
- Inspired by the Home Assistant community

---

⭐ If this integration is useful to you, please consider giving the project a star!
