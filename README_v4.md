# Home Assistant Cover Time Based (v4.0)

A Home Assistant custom integration for time-based cover control with **position-time maps** for accurate, non-linear movement tracking. Now with **UI Configuration**!

## 🎉 What's New in v4.0

- **✨ UI Configuration**: No more YAML editing! Configure covers through Home Assistant's UI
- **🔧 Easy Management**: Add, edit, and remove covers from Settings > Devices & Services
- **🔄 Live Reconfiguration**: Update cover settings without restarting Home Assistant
- **📱 Modern Integration**: Follows Home Assistant's latest integration standards
- **🔙 Backward Compatible**: Existing YAML configurations continue to work

## ⚠️ Breaking Changes from v3.0

- **NEW**: UI-based configuration (recommended)
- **KEPT**: YAML configuration (legacy support)
- **SAME**: All time map functionality and features

## Features

- **Non-linear movement profiles**: Define exact position at specific time intervals
- **Accurate position tracking**: Real-world cover behavior modeling
- **Interpolation**: Smooth position calculation between defined points
- **Target positioning**: Precise movement to any position
- **State persistence**: Position recovery after Home Assistant restart
- **Tilt support**: Optional linear tilt control
- **Switch-based control**: Support for open/close/stop switches
- **UI Configuration**: Easy setup and management through Home Assistant UI

## Installation

### HACS (Recommended)
1. Add this repository to HACS as a custom repository
2. Install "Cover Time Based" from HACS
3. Restart Home Assistant

### Manual Installation
1. Copy the `custom_components/cover_time_based` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

### UI Configuration (v4.0+) - Recommended

1. **Add Integration**:
   - Go to Settings > Devices & Services
   - Click "Add Integration"
   - Search for "Cover Time Based"
   - Click to add

2. **Configure Cover**:
   - **Name**: Enter a name for your cover
   - **Open Switch Entity**: Select the switch that opens the cover
   - **Close Switch Entity**: Select the switch that closes the cover
   - **Stop Switch Entity**: (Optional) Select the switch that stops the cover
   - **Switches are buttons**: Check if switches auto-turn off after activation
   - **Opening Time Map**: JSON format time-to-position mapping for opening
   - **Closing Time Map**: JSON format time-to-position mapping for closing
   - **Tilt Times**: (Optional) Time in seconds for tilt up/down movements

3. **Time Map Examples**:
   - **Linear movement**: `{"0": 0, "10": 100}`
   - **Non-linear**: `{"0": 0, "3": 20, "6": 50, "8": 80, "10": 100}`

4. **Add Multiple Covers**:
   - Repeat the process to add more covers
   - Each cover is configured separately
   - Edit individual covers anytime from the integration page

### Example UI Configuration

**Basic Linear Cover:**
```
Name: Bedroom Cover
Open Switch: switch.bedroom_cover_open
Close Switch: switch.bedroom_cover_close
Opening Time Map: {"0": 0, "10": 100}
Closing Time Map: {"0": 100, "10": 0}
```

**Advanced Non-Linear Cover with Tilt:**
```
Name: Living Room Blinds
Open Switch: switch.living_room_open
Close Switch: switch.living_room_close
Stop Switch: switch.living_room_stop
Opening Time Map: {"0": 0, "3": 20, "6": 50, "8": 80, "10": 100}
Closing Time Map: {"0": 100, "2": 80, "5": 50, "8": 20, "10": 0}
Tilt Down Time: 2.0
Tilt Up Time: 2.0
```

### YAML Configuration (Legacy)

For backward compatibility, YAML configuration still works:

```yaml
cover:
  - platform: cover_time_based
    devices:
      bedroom_cover:
        name: "Bedroom Cover"
        open_switch_entity_id: switch.bedroom_cover_open
        close_switch_entity_id: switch.bedroom_cover_close
        opening_time_map:
          0: 0
          10: 100
        closing_time_map:
          0: 100
          10: 0
```

## Time Maps

Time maps define the relationship between elapsed time and cover position:

- **Keys**: Time in seconds (must start with 0)
- **Values**: Position percentage (0-100, where 0=closed, 100=open)
- **Opening maps**: Must start at position 0 and end at position 100
- **Closing maps**: Must start at position 100 and end at position 0
- **Positions must be monotonic** (non-decreasing for opening, non-increasing for closing)

### Time Map Examples

**Linear movement (10 seconds):**
```json
{
  "0": 0,
  "10": 100
}
```

**Fast start, slow finish:**
```json
{
  "0": 0,
  "2": 40,
  "5": 70,
  "8": 90,
  "10": 100
}
```

**Slow start, fast finish:**
```json
{
  "0": 0,
  "5": 20,
  "7": 50,
  "9": 90,
  "10": 100
}
```

## Management

### Adding Covers
1. Go to Settings > Devices & Services
2. Find "Cover Time Based" integration
3. Click "Add Entry" or the "+" button
4. Configure the new cover

### Editing Covers
1. Go to Settings > Devices & Services
2. Find "Cover Time Based" integration
3. Click on the cover entry you want to edit
4. Click "Configure"
5. Update settings and save

### Removing Covers
1. Go to Settings > Devices & Services
2. Find the cover entry you want to remove
3. Click the three dots menu
4. Select "Delete"

## Services

### `cover_time_based.set_known_position`
Set a known position for the cover (useful for calibration).

```yaml
service: cover_time_based.set_known_position
target:
  entity_id: cover.bedroom_cover
data:
  position: 50
```

### `cover_time_based.set_known_tilt_position`
Set a known tilt position for the cover.

```yaml
service: cover_time_based.set_known_tilt_position
target:
  entity_id: cover.office_blinds
data:
  position: 75
```

## Migration from v3.0

### Option 1: Keep YAML Configuration
Your existing YAML configuration will continue to work. No changes needed.

### Option 2: Migrate to UI Configuration
1. **Note your current settings** from YAML
2. **Remove YAML configuration** from `configuration.yaml`
3. **Restart Home Assistant**
4. **Add integration** through UI using your noted settings
5. **Test the cover** works as expected

### Migration Example

**Old YAML (v3.0):**
```yaml
cover:
  - platform: cover_time_based
    devices:
      bedroom_cover:
        name: "Bedroom Cover"
        open_switch_entity_id: switch.bedroom_open
        close_switch_entity_id: switch.bedroom_close
        opening_time_map:
          0: 0
          12: 100
        closing_time_map:
          0: 100
          15: 0
```

**New UI Configuration (v4.0):**
- Name: `Bedroom Cover`
- Open Switch: `switch.bedroom_open`
- Close Switch: `switch.bedroom_close`
- Opening Time Map: `{"0": 0, "12": 100}`
- Closing Time Map: `{"0": 100, "15": 0}`

## Troubleshooting

### Cover doesn't appear in UI
- Restart Home Assistant after installation
- Check that the integration is properly installed in `custom_components/cover_time_based/`

### Time map validation errors
- Ensure JSON format is correct: `{"0": 0, "10": 100}`
- Opening maps must start at 0 and end at 100
- Closing maps must start at 100 and end at 0
- Positions must be monotonic (always increasing for opening, decreasing for closing)

### Cover doesn't move to correct position
- Check that your time maps accurately reflect your cover's movement
- Use the `set_known_position` service to calibrate
- Verify switch entities are working correctly

### Entity not found errors
- Ensure switch entities exist and are spelled correctly
- Check that switches are accessible from Home Assistant

## Debug Logging

Add to your `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.cover_time_based: debug
```

## Roadmap

- **Entity-based covers**: Support for existing cover entities (not just switches)
- **Visual time map editor**: Graphical interface for creating time maps
- **Templates**: Pre-built time maps for common cover types
- **Import/Export**: Share time map configurations

## License

This project is licensed under the MIT License.

## Support

- **Issues**: [GitHub Issues](https://github.com/mikipal7/ha-cover-time-based/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mikipal7/ha-cover-time-based/discussions)
- **Documentation**: This README and inline code comments