# Upgrade Guide: Cover Time Based v3.0 → v4.0

## 🎉 Welcome to v4.0!

Your Cover Time Based integration now supports **UI Configuration**! This means you can configure covers through Home Assistant's interface instead of editing YAML files.

## What's Changed

### ✅ New Features
- **UI Configuration**: Add and configure covers through Settings > Devices & Services
- **Live Reconfiguration**: Edit cover settings without restarting Home Assistant
- **Multiple Covers**: Add covers one at a time, edit individually
- **Modern Integration**: Follows Home Assistant's latest standards

### ✅ What Stays the Same
- **All functionality**: Time maps, tilt support, position tracking
- **YAML Support**: Your existing configuration continues to work
- **Services**: All custom services remain available
- **Entity IDs**: Your existing entities keep the same IDs

## Installation Steps

1. **Update the Integration**:
   - Through HACS: Update "Cover Time Based" 
   - Manual: Replace files in `custom_components/cover_time_based/`

2. **Restart Home Assistant**

3. **Choose Your Path**:
   - **Keep YAML**: No changes needed, everything works as before
   - **Switch to UI**: Follow migration steps below

## Migration Options

### Option A: Keep YAML Configuration (Easiest)
Your existing configuration will continue to work. No action needed!

### Option B: Migrate to UI Configuration (Recommended)

#### Step 1: Note Your Current Settings
Before making changes, document your current YAML configuration:

```yaml
# Example of what to note down:
cover:
  - platform: cover_time_based
    devices:
      bedroom_cover:
        name: "Bedroom Cover"
        open_switch_entity_id: switch.bedroom_open
        close_switch_entity_id: switch.bedroom_close
        opening_time_map:
          0: 0
          10: 100
        closing_time_map:
          0: 100
          12: 0
```

#### Step 2: Add Through UI
1. Go to **Settings > Devices & Services**
2. Click **"Add Integration"**
3. Search for **"Cover Time Based"**
4. Configure each cover using your noted settings:
   - **Name**: `Bedroom Cover`
   - **Open Switch**: `switch.bedroom_open`
   - **Close Switch**: `switch.bedroom_close`
   - **Opening Time Map**: `{"0": 0, "10": 100}`
   - **Closing Time Map**: `{"0": 100, "12": 0}`

#### Step 3: Test
Test that your covers work correctly with the new UI configuration.

#### Step 4: Remove YAML (Optional)
Once confirmed working, remove the YAML configuration from `configuration.yaml` and restart.

## Time Map Format Change

### YAML Format (v3.0):
```yaml
opening_time_map:
  0: 0
  10: 100
```

### UI Format (v4.0):
```json
{"0": 0, "10": 100}
```

The UI uses JSON format for time maps. This allows for easy copy/paste and validation.

## Common Migration Examples

### Simple Linear Cover
**YAML:**
```yaml
bedroom_cover:
  name: "Bedroom Cover"
  open_switch_entity_id: switch.bedroom_open
  close_switch_entity_id: switch.bedroom_close
  opening_time_map:
    0: 0
    10: 100
  closing_time_map:
    0: 100
    10: 0
```

**UI Configuration:**
- Name: `Bedroom Cover`
- Open Switch: `switch.bedroom_open`
- Close Switch: `switch.bedroom_close`
- Opening Time Map: `{"0": 0, "10": 100}`
- Closing Time Map: `{"0": 100, "10": 0}`

### Advanced Cover with Tilt
**YAML:**
```yaml
office_blinds:
  name: "Office Blinds"
  open_switch_entity_id: switch.office_open
  close_switch_entity_id: switch.office_close
  stop_switch_entity_id: switch.office_stop
  is_button: true
  opening_time_map:
    0: 0
    3: 20
    6: 50
    8: 80
    10: 100
  closing_time_map:
    0: 100
    2: 80
    5: 50
    8: 20
    10: 0
  tilting_time_down: 2.0
  tilting_time_up: 2.0
```

**UI Configuration:**
- Name: `Office Blinds`
- Open Switch: `switch.office_open`
- Close Switch: `switch.office_close`
- Stop Switch: `switch.office_stop`
- Switches are buttons: `✓ Yes`
- Opening Time Map: `{"0": 0, "3": 20, "6": 50, "8": 80, "10": 100}`
- Closing Time Map: `{"0": 100, "2": 80, "5": 50, "8": 20, "10": 0}`
- Tilt Down Time: `2.0`
- Tilt Up Time: `2.0`

## Troubleshooting

### Integration Not Found
- Restart Home Assistant after updating
- Clear browser cache
- Check that files are in `custom_components/cover_time_based/`

### Time Map Validation Errors
- Use proper JSON format: `{"0": 0, "10": 100}`
- Opening maps: start at 0, end at 100
- Closing maps: start at 100, end at 0
- Positions must be monotonic (always increasing/decreasing)

### Entity ID Changes
Entity IDs should remain the same. If they change:
- Check the integration entry name
- Update automations/scripts if needed
- Use the entity registry to rename if necessary

## Benefits of UI Configuration

1. **Easier Management**: No YAML editing required
2. **Validation**: Real-time validation of time maps
3. **Multiple Covers**: Add covers individually over time
4. **Live Updates**: Change settings without restart
5. **User Friendly**: Intuitive interface for all users

## Need Help?

- **Documentation**: Check the updated README
- **Issues**: Report problems on GitHub
- **Migration**: Use the migration helper script if needed

## Rollback Plan

If you need to rollback to v3.0:
1. Restore v3.0 files
2. Keep your YAML configuration
3. Restart Home Assistant

Your YAML configuration will work immediately with v3.0.

---

**Enjoy the new UI configuration! 🎉**