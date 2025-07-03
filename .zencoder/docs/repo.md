# Home Assistant Cover Time Based Information

## Summary
A Home Assistant custom component for time-based cover control with position-time maps for accurate, non-linear movement tracking. This integration allows precise control of covers (blinds, shutters, etc.) by defining exact position at specific time intervals, enabling accurate modeling of real-world cover behavior.

## Structure
- **custom_components/**: Contains the Home Assistant integration code
  - **cover_time_based/**: Main integration package with component implementation
- **.github/**: CI/CD workflows for HACS and hassfest validation
- **test_integration.py**: Script to validate integration structure
- **test_json_parsing.py**: Script to test JSON parsing functionality
- **debug_time_map.py**: Utility for debugging time maps

## Language & Runtime
**Language**: Python
**Version**: Python 3.x (compatible with Home Assistant requirements)
**Integration Type**: Home Assistant Custom Component
**Package Manager**: None (direct installation)

## Dependencies
**Main Dependencies**:
- Home Assistant Core
- No external Python package dependencies

**Development Dependencies**:
- Home Assistant development environment
- hassfest validation tools
- HACS validation tools

## Build & Installation
### HACS Installation (Recommended)
```bash
# Add repository to HACS as a custom repository
# Install "Cover Time Based" from HACS
# Restart Home Assistant
```

### Manual Installation
```bash
# Copy the custom_components/cover_time_based folder to Home Assistant custom_components directory
# Restart Home Assistant
```

## Testing
**Framework**: Custom test scripts
**Test Files**:
- **test_integration.py**: Validates integration structure and files
- **test_json_parsing.py**: Tests JSON parsing functionality

**Run Command**:
```bash
python test_integration.py
```

## Configuration
The component is configured through Home Assistant's configuration.yaml or through the UI config flow:

```yaml
cover:
  - platform: cover_time_based
    devices:
      bedroom_cover:
        name: "Bedroom Cover"
        open_switch_entity_id: switch.bedroom_cover_open
        close_switch_entity_id: switch.bedroom_cover_close
        opening_time_map:
          0: 0    # At 0 seconds, position is 0% (closed)
          10: 100 # At 10 seconds, position is 100% (open)
        closing_time_map:
          0: 100  # At 0 seconds, position is 100% (open)
          10: 0   # At 10 seconds, position is 0% (closed)
```

## Services
The integration provides custom services:
- **cover_time_based.set_known_position**: Set a known position for the cover
- **cover_time_based.set_known_tilt_position**: Set a known tilt position for the cover

## CI/CD
**Workflows**:
- **hassfest.yml**: Validates the integration against Home Assistant standards
- **hacs.yml**: Validates the integration for HACS compatibility

## Version History
Current version: 4.0.0 (according to manifest.json)
Previous major version: 3.0.0 (with breaking changes from v2.x)