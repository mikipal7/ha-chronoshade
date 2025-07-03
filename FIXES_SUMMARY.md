# Fixes Applied - Cover Time Based v4.0

## Issues Fixed

### 1. ✅ Entity Selector Limitation
**Problem**: Entity selectors only allowed switches, couldn't select scripts or automations.

**Solution**: 
- Updated `config_flow.py` to allow multiple entity domains: `["switch", "script", "automation", "input_boolean"]`
- Updated both user and reconfigure schemas
- Added proper service calling logic in `cover.py` to handle different entity types

**Files Changed**:
- `config_flow.py` - Updated EntitySelector configurations
- `cover.py` - Added `_async_call_entity_service()` method
- `cover.py` - Updated `_async_handle_command()` to use new service method

### 2. ✅ Integration Type (Helper vs Device)
**Problem**: Integration was classified as "helper" so it didn't appear in the devices screen.

**Solution**:
- Changed `integration_type` from "helper" to "device" in `manifest.json`
- Changed `iot_class` from "calculated" to "local_push" (more appropriate for device)
- Added `device_info` property to `CoverTimeBased` class to provide device information

**Files Changed**:
- `manifest.json` - Updated integration_type and iot_class
- `cover.py` - Added DeviceInfo import and device_info property

### 3. ✅ Entity Service Handling
**Problem**: All entities were treated as switches with turn_on/turn_off services.

**Solution**:
- Created `_async_call_entity_service()` method to handle different entity types:
  - **Scripts**: Use `script.turn_on` service (ignore turn_off)
  - **Automations**: Use `automation.trigger` service (ignore turn_off)  
  - **Switches/Input Booleans**: Use `homeassistant.turn_on/turn_off` services

**Logic**:
```python
if domain == "script":
    if action == "turn_on":
        await self.hass.services.async_call("script", "turn_on", {"entity_id": entity_id}, False)
elif domain == "automation":
    if action == "turn_on":
        await self.hass.services.async_call("automation", "trigger", {"entity_id": entity_id}, False)
else:
    await self.hass.services.async_call("homeassistant", action, {"entity_id": entity_id}, False)
```

### 4. ✅ UI Text Updates
**Problem**: UI still referred to "switches" only.

**Solution**:
- Updated all UI text to reflect support for multiple entity types
- Changed "Switch Entity" to "Entity (Switch/Script/Automation)"
- Updated "Switches are buttons" to "Entities are buttons/momentary"
- Applied changes to English and Portuguese translations

**Files Changed**:
- `strings.json`
- `translations/en.json`
- `translations/pt.json`

### 5. ✅ Test Validation
**Problem**: Test script didn't validate the new device integration type.

**Solution**:
- Updated `test_integration.py` to check for `integration_type: "device"`

## Current Capabilities

### Entity Types Supported
- ✅ **Switches** - Traditional on/off switches
- ✅ **Scripts** - Home Assistant scripts (triggered with script.turn_on)
- ✅ **Automations** - Home Assistant automations (triggered with automation.trigger)
- ✅ **Input Booleans** - Virtual switches

### Integration Behavior
- ✅ **Appears in Devices screen** (not just integrations)
- ✅ **Proper device information** with manufacturer, model, version
- ✅ **Multiple covers** as separate device entries
- ✅ **Individual management** of each cover

### Service Handling
- ✅ **Smart service calling** based on entity domain
- ✅ **Graceful handling** of unsupported operations (e.g., turn_off for scripts)
- ✅ **Backward compatibility** with existing switch-based configurations

## Usage Examples

### With Scripts
```
Open Entity: script.open_bedroom_cover
Close Entity: script.close_bedroom_cover
Stop Entity: script.stop_bedroom_cover
```

### With Automations
```
Open Entity: automation.bedroom_cover_open
Close Entity: automation.bedroom_cover_close
Stop Entity: automation.bedroom_cover_stop
```

### Mixed Types
```
Open Entity: switch.cover_open
Close Entity: script.cover_close_sequence
Stop Entity: automation.emergency_stop
```

## Testing Recommendations

1. **Test with switches** - Verify existing functionality still works
2. **Test with scripts** - Verify scripts are triggered correctly
3. **Test with automations** - Verify automations are triggered correctly
4. **Test device appearance** - Verify covers appear in Settings > Devices & Services
5. **Test reconfiguration** - Verify you can edit existing covers
6. **Test multiple covers** - Verify you can add multiple covers independently

## Next Steps

1. **Test in real Home Assistant environment**
2. **Verify device information appears correctly**
3. **Test with actual scripts and automations**
4. **Update documentation** to reflect new capabilities
5. **Consider adding validation** for entity existence during configuration

---

# Latest Fixes (Current Session)

## Issues Fixed

### 6. ✅ Config Flow Reconfigure Problem
**Problem**: When editing an existing device, the form required open/close/stop entities despite having "use existing cover" checked and a cover selected. This didn't happen during initial creation.

**Root Cause**: The reconfigure method's validation logic was identical to the initial setup, but it didn't properly handle the conditional validation based on the "use existing cover" setting.

**Solution**:
- Updated `async_step_reconfigure` method in `config_flow.py` to properly handle the "use existing cover" option
- Added support for simple mode configuration in reconfigure (was missing)
- Fixed validation logic to skip switch entity requirements when "use existing cover" is checked
- Updated `_get_reconfigure_schema` to include simple mode fields
- Improved error handling in reconfigure flow

**Files Modified**:
- `custom_components/cover_time_based/config_flow.py`

### 7. ✅ Devices Not Provided After Home Assistant Updates
**Problem**: After Home Assistant updates, existing devices configured with this integration stopped working and showed as "not provided anymore". The only solution was to delete and recreate them.

**Root Cause**: The unique_id was based on the config entry ID, which could change across Home Assistant updates, causing the system to lose track of existing entities.

**Solution**:
- Changed unique_id generation to be based on the device name instead of config entry ID
- Implemented proper unique_id sanitization using regex to ensure valid characters
- Added migration mechanism to handle existing installations
- Updated config flow version from 1 to 2 to trigger migration
- Added `async_migrate_entry` function to migrate existing entries to the new unique_id format

**Files Modified**:
- `custom_components/cover_time_based/cover.py`
- `custom_components/cover_time_based/config_flow.py`
- `custom_components/cover_time_based/__init__.py`

## Technical Details

### Unique ID Generation
- **Old**: Used config entry ID (unstable across HA updates)
- **New**: Uses sanitized device name (`re.sub(r'[^a-z0-9_]', '_', name.lower())`)
- **Migration**: Automatically converts existing entries to new format

### Config Flow Improvements
- Enhanced validation logic for reconfigure flow
- Added simple mode support in reconfigure
- Improved error handling and user feedback
- Maintained backward compatibility

### Migration Strategy
- Version bump from 1 to 2 triggers automatic migration
- Preserves all existing configuration data
- Updates unique_id to stable name-based format
- Graceful fallback if migration fails

## Testing Recommendations for Latest Fixes

1. **Test Issue 6 Fix**:
   - Create a new device using "existing cover" option
   - Edit the device configuration
   - Verify that switch entities are not required when "use existing cover" is checked

2. **Test Issue 7 Fix**:
   - Existing installations should automatically migrate on restart
   - New installations should use stable unique_ids
   - Devices should persist across Home Assistant updates

## Backward Compatibility

- All existing configurations will be automatically migrated
- No manual intervention required from users
- Configuration data remains unchanged
- Only unique_id generation method is updated

## Version Information

- Config Flow Version: Updated from 1 to 2
- Integration Version: 4.0.0 (unchanged)
- Migration: Automatic on first load after update