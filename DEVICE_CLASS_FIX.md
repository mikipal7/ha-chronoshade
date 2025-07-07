# Device Class Fix for Alexa and Google Home Integration

## Problem
- **Alexa**: Shows covers as "Others" category instead of proper cover type
- **Google Home**: Recognizes device type but controls don't work properly

## Root Cause
The cover entity was returning `None` for `device_class`, which prevents voice assistants from properly categorizing and controlling the devices.

## Solution Implemented

### 1. Added CoverDeviceClass Import
- Imported `CoverDeviceClass` from `homeassistant.components.cover`
- Added support for all Home Assistant cover device classes

### 2. Smart Device Class Detection
Implemented intelligent device class selection:
- **BLIND**: When tilt functionality is configured (blinds commonly have tilt)
- **SHADE**: When only position control is available (shades are typically position-only)

### 3. User Override Option
Added `device_class` configuration option allowing users to manually specify:
- awning, blind, curtain, damper, door, garage, gate, shade, shutter, window
- Auto-detect option (default behavior)

### 4. Configuration Integration
Updated all config flow schemas to include device class selection:
- Standard configuration modes
- Advanced configuration modes  
- Automatic configuration modes
- Both switch-based and existing cover methods

## Files Modified

### `custom_components/chronoshade/const.py`
- Added `CONF_DEVICE_CLASS = "device_class"`

### `custom_components/chronoshade/cover.py`
- Added `CoverDeviceClass` import
- Added `CONF_DEVICE_CLASS` import
- Updated schemas to include device class option
- Implemented smart `device_class` property with auto-detection logic
- Added device class configuration to `__init__` method

### `custom_components/chronoshade/config_flow.py`
- Added `CONF_DEVICE_CLASS` import
- Added device class selector to all configuration schemas
- Updated all data processing sections to include device class

## How It Works

### Auto-Detection Logic
```python
@property
def device_class(self):
    """Return the device class of the cover."""
    # If user explicitly set a device class, use it
    if self._device_class:
        if isinstance(self._device_class, str):
            try:
                return getattr(CoverDeviceClass, self._device_class.upper())
            except AttributeError:
                _LOGGER.warning("Invalid device class '%s', using auto-detection", self._device_class)
        else:
            return self._device_class
    
    # Auto-detect based on tilt support
    if self._has_tilt_support():
        return CoverDeviceClass.BLIND  # Blinds commonly have tilt functionality
    else:
        return CoverDeviceClass.SHADE  # Shades are typically position-only covers
```

### Configuration Options
Users can now select device class during setup:
- **Auto-detect**: Smart selection based on tilt configuration
- **Manual selection**: Choose from all supported cover types

## Expected Results

### Alexa Integration
- Covers should now appear in proper category (e.g., "Blinds", "Shades")
- Voice commands should work: "Alexa, open the bedroom blinds"
- App controls should be available with proper icons

### Google Home Integration
- Device type recognition should be maintained
- Position controls should work properly
- Voice commands should be more reliable

## Testing Instructions

1. **Restart Home Assistant** after updating the integration
2. **Reconfigure existing covers** to apply device class settings
3. **Test voice commands**:
   - "Hey Google, open the [cover name]"
   - "Alexa, close the [cover name] to 50%"
4. **Check mobile apps** for proper categorization and controls

## Backward Compatibility
- Existing configurations will use auto-detection
- No breaking changes to existing setups
- Users can optionally reconfigure to set specific device classes

## Migration for Existing Users
1. Go to Settings → Devices & Services → ChronoShade
2. Click "Configure" on existing covers
3. Select appropriate device class or leave as "Auto-detect"
4. Save configuration
5. Test voice assistant integration