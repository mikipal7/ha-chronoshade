# 🚀 Migration Guide: Cover Time Based → ChronoShade

Welcome to **ChronoShade**! This guide will help you migrate from the old "Cover Time Based" integration to the new and improved ChronoShade.

## 🎯 What's New in ChronoShade

- **Fixed Translation Errors**: No more `MALFORMED_ARGUMENT` errors in the UI
- **Modern Branding**: Fresh new name and professional appearance
- **Enhanced UI**: Improved config flow with better validation
- **Better Documentation**: Comprehensive guides and examples
- **Same Great Features**: All your favorite functionality, just better

## 🔄 Migration Steps

### Step 1: Remove Old Integration
1. Go to **Settings** → **Devices & Services**
2. Find your old "Cover Time Based" integrations
3. Click the three dots → **Delete**
4. Remove the old `custom_components/cover_time_based` folder

### Step 2: Install ChronoShade
1. Copy `custom_components/chronoshade` to your Home Assistant
2. Restart Home Assistant
3. Go to **Settings** → **Devices & Services** → **Add Integration**
4. Search for "ChronoShade"

### Step 3: Reconfigure Your Covers
Your old configuration will need to be recreated, but it's easy with the new UI:

#### Old YAML Configuration:
```yaml
cover:
  - platform: cover_time_based
    devices:
      bedroom_cover:
        name: "Bedroom Cover"
        # ... rest of config
```

#### New ChronoShade Configuration:
- Use the UI config flow (much easier!)
- Or update YAML to use `platform: chronoshade`

## 🛠️ Configuration Changes

### Domain Change
- **Old**: `cover_time_based`
- **New**: `chronoshade`

### Service Names
- **Old**: `cover_time_based.set_known_position`
- **New**: `chronoshade.set_known_position`

### Entity IDs
Your entity IDs will change:
- **Old**: `cover.bedroom_cover` (from cover_time_based)
- **New**: `cover.bedroom_cover` (from chronoshade)

## 🔧 Automation Updates

Update any automations that reference the old services:

### Before:
```yaml
service: cover_time_based.set_known_position
data:
  entity_id: cover.bedroom_cover
  position: 50
```

### After:
```yaml
service: chronoshade.set_known_position
data:
  entity_id: cover.bedroom_cover
  position: 50
```

## ✅ Verification Checklist

After migration, verify:
- [ ] All covers appear in Home Assistant
- [ ] Covers respond to open/close commands
- [ ] Position tracking works correctly
- [ ] Tilt functions work (if configured)
- [ ] No error messages in logs
- [ ] Automations using ChronoShade services work

## 🆘 Troubleshooting

### "Integration not found"
- Ensure you've copied the `chronoshade` folder correctly
- Restart Home Assistant
- Check the logs for any errors

### "Translation error" or UI issues
- Clear your browser cache
- Try a different browser
- Check that `strings.json` is properly formatted

### Covers not working
- Verify your switch entities still exist
- Check time maps are properly configured
- Use the `set_known_position` service to calibrate

## 🎉 Welcome to ChronoShade!

You're now using the most advanced time-based cover control integration for Home Assistant. Enjoy the improved experience and precision control!

For support, please check the [README](README.md) or open an issue on GitHub.

---

**ChronoShade** - *Precision in every movement* ⏱️