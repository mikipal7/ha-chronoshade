"""ChronoShade integration."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_NAME
from homeassistant.core import HomeAssistant


from .const import (
    DOMAIN,
    CONF_CONTROL_METHOD,
    CONF_COVER_ENTITY_ID,
    CONF_OPEN_SWITCH_ENTITY_ID,
    CONF_CLOSE_SWITCH_ENTITY_ID,
    CONF_DEVICE_CLASS,
    CONTROL_METHOD_SWITCHES,
    CONTROL_METHOD_EXISTING_COVER,
    CURRENT_CONFIG_VERSION,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.COVER]


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry to new version."""
    _LOGGER.debug("Migrating config entry from version %s", config_entry.version)

    new_data = dict(config_entry.data)
    new_version = config_entry.version
    
    # Migration from version 1 to 2: Add name-based unique_id
    if config_entry.version == 1:
        name = new_data.get(CONF_NAME, "")
        if name:
            new_unique_id = re.sub(r'[^a-z0-9_]', '_', name.lower())
            new_version = 2
        else:
            _LOGGER.error("Migration failed: no name found in config")
            return False
    
    # Migration from version 2 to 3: Add control method
    if config_entry.version <= 2:
        # Determine control method based on existing configuration
        if new_data.get(CONF_COVER_ENTITY_ID):
            new_data[CONF_CONTROL_METHOD] = CONTROL_METHOD_EXISTING_COVER
        elif new_data.get(CONF_OPEN_SWITCH_ENTITY_ID) and new_data.get(CONF_CLOSE_SWITCH_ENTITY_ID):
            new_data[CONF_CONTROL_METHOD] = CONTROL_METHOD_SWITCHES
        else:
            # Default to switches if unclear
            new_data[CONF_CONTROL_METHOD] = CONTROL_METHOD_SWITCHES
        
        new_version = 3
        
        # Generate stable unique_id if not already done
        if config_entry.version == 1:
            name = new_data.get(CONF_NAME, "")
            if name:
                new_unique_id = re.sub(r'[^a-z0-9_]', '_', name.lower())
            else:
                _LOGGER.error("Migration failed: no name found in config")
                return False
        else:
            new_unique_id = config_entry.unique_id
    
    # Migration from version 3 to 4: Add device class support
    if config_entry.version <= 3:
        # Add device_class field with empty default (auto-detect)
        if CONF_DEVICE_CLASS not in new_data:
            new_data[CONF_DEVICE_CLASS] = ""
        new_version = 4
    
    # Apply migration if needed
    if new_version > config_entry.version:
        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            unique_id=new_unique_id if 'new_unique_id' in locals() else config_entry.unique_id,
            version=new_version
        )
        
        _LOGGER.info("Migration to version %s successful", new_version)
        return True
    
    # No migration needed
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cover Time Based from a config entry."""
    # Ensure we have the latest config version
    if entry.version < CURRENT_CONFIG_VERSION:
        _LOGGER.warning(
            "Config entry version %s is older than current version %s. "
            "Migration should have been performed.",
            entry.version,
            CURRENT_CONFIG_VERSION
        )
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True





async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)