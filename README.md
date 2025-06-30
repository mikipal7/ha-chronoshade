# Home Assistant Cover Time Based (v3.0)

A Home Assistant custom component for time-based cover control with **position-time maps** for accurate, non-linear movement tracking.

## ⚠️ Breaking Changes in v3.0

This version completely redesigns the position calculation system:

- **REMOVED**: `travelling_time_down`, `travelling_time_up`, `opening_delay`, `closing_delay`
- **ADDED**: `opening_time_map` and `closing_time_map` (required)
- **REMOVED**: XKNX dependency
- **KEPT**: Tilt functionality with linear timing (unchanged)

## Features

- **Non-linear movement profiles**: Define exact position at specific time intervals
- **Accurate position tracking**: Real-world cover behavior modeling
- **Interpolation**: Smooth position calculation between defined points
- **Target positioning**: Precise movement to any position
- **State persistence**: Position recovery after Home Assistant restart
- **Tilt support**: Optional linear tilt control
- **Switch or entity control**: Support for both switch-based and entity-based covers

## Installation

### HACS (Recommended)
1. Add this repository to HACS as a custom repository
2. Install "Cover Time Based" from HACS
3. Restart Home Assistant

### Manual Installation
1. Copy the `custom_components/cover_time_based` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

### Basic Configuration

```yaml
cover:
  - platform: cover_time_based
    devices:
      bedroom_cover:
        name: "Bedroom Cover"
        open_switch_entity_id: switch.bedroom_cover_open
        close_switch_entity_id: switch.bedroom_cover_close
        stop_switch_entity_id: switch.bedroom_cover_stop  # optional
        opening_time_map:
          0: 0    # At 0 seconds, position is 0% (closed)
          10: 100 # At 10 seconds, position is 100% (open)
        closing_time_map:
          0: 100  # At 0 seconds, position is 100% (open)
          10: 0   # At 10 seconds, position is 0% (closed)
```

### Non-Linear Movement Example

```yaml
cover:
  - platform: cover_time_based
    devices:
      living_room_cover:
        name: "Living Room Cover"
        open_switch_entity_id: switch.living_room_cover_open
        close_switch_entity_id: switch.living_room_cover_close
        opening_time_map:
          0: 0    # Start closed
          3: 20   # After 3s, 20% open (slow start)
          6: 50   # After 6s, 50% open
          8: 80   # After 8s, 80% open (slowing down)
          10: 100 # After 10s, fully open
        closing_time_map:
          0: 100  # Start open
          2: 80   # After 2s, 80% open (fast start)
          5: 50   # After 5s, 50% open
          8: 20   # After 8s, 20% open
          10: 0   # After 10s, fully closed
```

### With Tilt Support

```yaml
cover:
  - platform: cover_time_based
    devices:
      office_blinds:
        name: "Office Blinds"
        open_switch_entity_id: switch.office_blinds_open
        close_switch_entity_id: switch.office_blinds_close
        opening_time_map:
          0: 0
          8: 100
        closing_time_map:
          0: 100
          8: 0
        tilting_time_down: 2.0  # 2 seconds to fully tilt down
        tilting_time_up: 2.0    # 2 seconds to fully tilt up
```

### Using Existing Cover Entity

```yaml
cover:
  - platform: cover_time_based
    devices:
      garage_door:
        name: "Garage Door"
        cover_entity_id: cover.garage_door_original
        opening_time_map:
          0: 0
          2: 10   # Slow start
          5: 50   # Mid-point
          12: 90  # Almost open
          15: 100 # Fully open
        closing_time_map:
          0: 100
          15: 0   # Linear closing
```

### Button-Style Switches

```yaml
cover:
  - platform: cover_time_based
    devices:
      patio_cover:
        name: "Patio Cover"
        open_switch_entity_id: switch.patio_cover_open
        close_switch_entity_id: switch.patio_cover_close
        is_button: true  # Switches turn off automatically after 1 second
        opening_time_map:
          0: 0
          12: 100
        closing_time_map:
          0: 100
          12: 0
```

## Configuration Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Display name for the cover |
| `opening_time_map` | dict | Time-to-position mapping for opening movement |
| `closing_time_map` | dict | Time-to-position mapping for closing movement |

### Switch-Based Covers

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `open_switch_entity_id` | string | - | Entity ID for open switch |
| `close_switch_entity_id` | string | - | Entity ID for close switch |
| `stop_switch_entity_id` | string | None | Entity ID for stop switch (optional) |
| `is_button` | boolean | false | If true, switches auto-turn off after 1 second |

### Entity-Based Covers

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cover_entity_id` | string | - | Entity ID of existing cover to control |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tilting_time_down` | float | None | Time in seconds for full tilt down |
| `tilting_time_up` | float | None | Time in seconds for full tilt up |

## Time Maps

Time maps define the relationship between elapsed time and cover position:

- **Keys**: Time in seconds (must start with 0)
- **Values**: Position percentage (0-100, where 0=closed, 100=open)
- **Opening maps**: Must start at position 0 and end at position 100
- **Closing maps**: Must start at position 100 and end at position 0
- **Positions must be monotonic** (non-decreasing for opening, non-increasing for closing)

### Examples

**Linear movement:**
```yaml
opening_time_map:
  0: 0
  10: 100
```

**Fast start, slow finish:**
```yaml
opening_time_map:
  0: 0
  2: 40
  5: 70
  8: 90
  10: 100
```

**Slow start, fast finish:**
```yaml
opening_time_map:
  0: 0
  5: 20
  7: 50
  9: 90
  10: 100
```

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

## Migration from v2.x

1. **Remove old parameters** from your configuration:
   - `travelling_time_down`
   - `travelling_time_up`
   - `opening_delay`
   - `closing_delay`

2. **Add time maps** based on your old travel times:
   ```yaml
   # Old configuration:
   travelling_time_down: 15
   travelling_time_up: 12
   
   # New configuration:
   opening_time_map:
     0: 0
     12: 100
   closing_time_map:
     0: 100
     15: 0
   ```

3. **Test and adjust** time maps to match your cover's actual behavior

## Troubleshooting

### Cover doesn't move to correct position
- Check that your time maps accurately reflect your cover's movement
- Use the `set_known_position` service to calibrate
- Verify time map validation rules are followed

### Position tracking is inaccurate
- Measure actual movement times and update time maps
- Consider non-linear movement patterns
- Add more time points for better accuracy

### Cover stops at wrong position
- Check for obstacles or mechanical issues
- Verify target position calculation with debug logs
- Ensure time maps are monotonic

## Debug Logging

Add to your `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.cover_time_based: debug
```

## License

This project is licensed under the MIT License.
