# ChronoShade 🕐

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

**ChronoShade** is a precision time-based cover control integration for Home Assistant that revolutionizes how you manage blinds, shutters, and other covers. Unlike traditional cover controls that rely on simple open/close commands, ChronoShade uses advanced **position-time mapping** to provide accurate, non-linear movement tracking for perfect cover positioning every time.

## ✨ Key Features

- 🎯 **Precision Control**: Define exact positions at specific time intervals
- 📊 **Non-Linear Movement**: Model real-world cover behavior with custom time maps
- 🔄 **Dual Control Methods**: Use existing covers or individual switch entities
- 🎛️ **Tilt Support**: Full tilt position control for venetian blinds
- 🚀 **Easy Setup**: Simple mode for quick configuration, advanced mode for power users
- 🔧 **Flexible Integration**: Works with switches, scripts, automations, and existing covers
- 📱 **Modern UI**: Beautiful config flow with real-time validation

## 🚀 Quick Start

### HACS Installation (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots menu → "Custom repositories"
4. Add `https://github.com/mikipal7/ha-chronoshade` as an Integration
5. Search for "ChronoShade" and install
6. Restart Home Assistant
7. Go to Settings → Devices & Services → Add Integration
8. Search for "ChronoShade"

### Manual Installation

1. Download the latest release
2. Copy `custom_components/chronoshade` to your Home Assistant `custom_components` directory
3. Restart Home Assistant
4. Add the integration via the UI

## 📖 Configuration

ChronoShade offers two configuration modes:

### Simple Mode (Recommended for beginners)
Perfect for covers with linear movement:
- Enter total opening/closing time
- System automatically creates optimal time maps

### Advanced Mode (For power users)
Full control with JSON time maps:
```json
{
  "0": 0,    // At 0 seconds: 0% (closed)
  "5": 30,   // At 5 seconds: 30% open
  "10": 80,  // At 10 seconds: 80% open
  "15": 100  // At 15 seconds: 100% (fully open)
}
```

## 🎛️ Control Methods

### Method 1: Individual Switches
Use separate entities for open/close/stop operations:
- **Open Entity**: Switch, script, or automation to open the cover
- **Close Entity**: Switch, script, or automation to close the cover
- **Stop Entity**: (Optional) Entity to stop movement

### Method 2: Existing Cover
Enhance an existing Home Assistant cover entity with precision timing.

## 🔧 Services

ChronoShade provides custom services for advanced control:

### `chronoshade.set_known_position`
Set a known position for calibration:
```yaml
service: chronoshade.set_known_position
data:
  entity_id: cover.bedroom_blinds
  position: 50
```

### `chronoshade.set_known_tilt_position`
Set a known tilt position:
```yaml
service: chronoshade.set_known_tilt_position
data:
  entity_id: cover.bedroom_blinds
  position: 75
```

## 📊 Example Configurations

### Basic Linear Cover
```yaml
# Configuration.yaml (if using YAML)
cover:
  - platform: chronoshade
    devices:
      living_room_blinds:
        name: "Living Room Blinds"
        open_switch_entity_id: switch.blinds_open
        close_switch_entity_id: switch.blinds_close
        opening_time_map:
          0: 0
          12: 100
        closing_time_map:
          0: 100
          12: 0
```

### Advanced Non-Linear Cover
Perfect for covers that move faster at the beginning:
```yaml
cover:
  - platform: chronoshade
    devices:
      bedroom_shutters:
        name: "Bedroom Shutters"
        open_switch_entity_id: script.shutters_open
        close_switch_entity_id: script.shutters_close
        stop_switch_entity_id: script.shutters_stop
        opening_time_map:
          0: 0     # Closed
          3: 40    # Fast initial movement
          8: 70    # Slower middle section
          15: 100  # Final positioning
        closing_time_map:
          0: 100   # Open
          4: 60    # Quick start
          10: 30   # Gradual closing
          15: 0    # Fully closed
        tilting_time_down: 2.5
        tilting_time_up: 2.5
```

## 🎯 Why ChronoShade?

Traditional cover integrations assume linear movement, but real covers don't work that way:
- **Motors vary in speed** during operation
- **Mechanical resistance** changes throughout the movement
- **Weight distribution** affects movement patterns
- **Wear and age** impact timing

ChronoShade solves this by letting you map the **actual behavior** of your covers, ensuring perfect positioning every time.

## 🔍 Troubleshooting

### Cover doesn't reach the exact position
1. Use the `set_known_position` service to calibrate
2. Adjust your time maps based on observed behavior
3. Consider mechanical factors like friction and wear

### Tilt function not working
1. Ensure `tilting_time_down` and `tilting_time_up` are configured
2. Verify your cover supports tilt operations
3. Check that tilt commands are properly mapped to your hardware

### Integration not appearing
1. Verify the `custom_components/chronoshade` directory exists
2. Check Home Assistant logs for errors
3. Ensure you've restarted Home Assistant after installation

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built for the Home Assistant community
- Inspired by real-world cover control challenges
- Thanks to all contributors and testers

---

**ChronoShade** - *Precision in every movement* ⏱️

[releases-shield]: https://img.shields.io/github/release/mikipal7/ha-chronoshade.svg?style=for-the-badge
[releases]: https://github.com/mikipal7/ha-chronoshade/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/mikipal7/ha-chronoshade.svg?style=for-the-badge
[commits]: https://github.com/mikipal7/ha-chronoshade/commits/main
[license-shield]: https://img.shields.io/github/license/mikipal7/ha-chronoshade.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge