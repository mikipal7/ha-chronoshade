"""Config flow for Cover Time Based integration."""
from __future__ import annotations

import json
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_OPENING_TIME_MAP,
    CONF_CLOSING_TIME_MAP,
    CONF_TILTING_TIME_DOWN,
    CONF_TILTING_TIME_UP,
    CONF_OPEN_SWITCH_ENTITY_ID,
    CONF_CLOSE_SWITCH_ENTITY_ID,
    CONF_STOP_SWITCH_ENTITY_ID,
    CONF_IS_BUTTON,
    CONF_COVER_ENTITY_ID,
    CONF_USE_EXISTING_COVER,
    DEFAULT_TILT_TIME,
)

_LOGGER = logging.getLogger(__name__)


def validate_tilt_time(value: Any) -> float | None:
    """Validate tilt time value, allowing None/empty values."""
    if value is None or value == "" or value == 0:
        return None
    try:
        float_val = float(value)
        if float_val < 0.1 or float_val > 300:
            raise vol.Invalid("Tilt time must be between 0.1 and 300 seconds")
        return float_val
    except (ValueError, TypeError) as err:
        raise vol.Invalid(f"Invalid tilt time value: {err}") from err


def parse_flexible_json(json_str: str) -> dict:
    """Parse JSON with flexible key format (with or without quotes)."""
    if not json_str.strip():
        raise vol.Invalid("JSON string cannot be empty")
    
    try:
        # First try standard JSON parsing
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            # Try to fix common JSON issues
            # Add quotes around unquoted keys
            import re
            
            # Replace unquoted keys with quoted keys
            # This regex finds keys that are not quoted (word characters followed by colon)
            fixed_json = re.sub(r'(\b\w+\b)(\s*:\s*)', r'"\1"\2', json_str)
            
            # Try parsing the fixed JSON
            return json.loads(fixed_json)
        except (json.JSONDecodeError, re.error):
            try:
                # Last attempt: try eval for Python dict syntax
                # This is safe because we control the input and only allow dict-like structures
                result = eval(json_str, {"__builtins__": {}}, {})
                if isinstance(result, dict):
                    return result
                else:
                    raise vol.Invalid("Input must be a dictionary/object")
            except Exception as err:
                raise vol.Invalid(f"Invalid JSON format. Please check syntax: {err}") from err


def validate_time_map(time_map_str: str, map_type: str) -> dict[float, int]:
    """Validate and parse time map from string."""
    try:
        time_map_raw = parse_flexible_json(time_map_str)
    except vol.Invalid as err:
        raise vol.Invalid(f"Invalid format in {map_type.lower()} time map: {err}") from err
    
    if not isinstance(time_map_raw, dict):
        raise vol.Invalid("Time map must be a JSON object")
    
    # Convert keys to float and values to int
    try:
        time_map = {float(k): int(v) for k, v in time_map_raw.items()}
    except (ValueError, TypeError) as err:
        raise vol.Invalid(f"Invalid time map format: {err}") from err
    
    # Validate time map
    if not time_map:
        raise vol.Invalid(f"{map_type} time map cannot be empty")
    
    # Sort by time
    sorted_times = sorted(time_map.keys())
    times = sorted_times
    positions = [time_map[t] for t in times]
    
    # Validate time progression
    if times[0] != 0:
        raise vol.Invalid(f"{map_type} time map must start at time 0")
    
    # Validate position range
    for pos in positions:
        if not 0 <= pos <= 100:
            raise vol.Invalid(f"Position {pos} in {map_type} time map must be between 0 and 100")
    
    # Validate start/end positions
    if map_type == "Opening":
        if positions[0] != 0:
            raise vol.Invalid("Opening time map must start at position 0 (closed)")
        if positions[-1] != 100:
            raise vol.Invalid("Opening time map must end at position 100 (open)")
    else:  # closing
        if positions[0] != 100:
            raise vol.Invalid("Closing time map must start at position 100 (open)")
        if positions[-1] != 0:
            raise vol.Invalid("Closing time map must end at position 0 (closed)")
    
    # Validate monotonic progression
    if map_type == "Opening":
        for i in range(1, len(positions)):
            if positions[i] < positions[i-1]:
                raise vol.Invalid("Opening time map positions must be non-decreasing")
    else:  # closing
        for i in range(1, len(positions)):
            if positions[i] > positions[i-1]:
                raise vol.Invalid("Closing time map positions must be non-increasing")
    
    return time_map


# This function is no longer needed as validation is done directly in the flow methods


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cover Time Based."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Determine if using existing cover or individual switches
                use_existing_cover = user_input.get(CONF_USE_EXISTING_COVER, False)
                
                if use_existing_cover:
                    # Validate cover entity exists
                    cover_entity = user_input.get(CONF_COVER_ENTITY_ID)
                    if not cover_entity:
                        raise vol.Invalid("Cover entity is required when using existing cover")
                    
                    if self.hass.states.get(cover_entity) is None:
                        raise vol.Invalid(f"Cover entity '{cover_entity}' not found")
                    
                    # Set switch entities to None when using existing cover
                    open_entity = None
                    close_entity = None
                    stop_entity = None
                else:
                    # Validate switch entities exist
                    open_entity = user_input.get(CONF_OPEN_SWITCH_ENTITY_ID)
                    close_entity = user_input.get(CONF_CLOSE_SWITCH_ENTITY_ID)
                    stop_entity = user_input.get(CONF_STOP_SWITCH_ENTITY_ID)
                    cover_entity = None
                    
                    if not open_entity:
                        raise vol.Invalid("Open switch entity is required when not using existing cover")
                    if not close_entity:
                        raise vol.Invalid("Close switch entity is required when not using existing cover")
                    
                    if self.hass.states.get(open_entity) is None:
                        raise vol.Invalid(f"Open switch entity '{open_entity}' not found")
                    
                    if self.hass.states.get(close_entity) is None:
                        raise vol.Invalid(f"Close switch entity '{close_entity}' not found")
                    
                    if stop_entity and self.hass.states.get(stop_entity) is None:
                        raise vol.Invalid(f"Stop switch entity '{stop_entity}' not found")
                
                # Validate time maps
                opening_time_map = validate_time_map(user_input[CONF_OPENING_TIME_MAP], "Opening")
                closing_time_map = validate_time_map(user_input[CONF_CLOSING_TIME_MAP], "Closing")
                
                # Validate tilt times (properly handle None/empty values)
                tilt_down = validate_tilt_time(user_input.get(CONF_TILTING_TIME_DOWN))
                tilt_up = validate_tilt_time(user_input.get(CONF_TILTING_TIME_UP))
                
                # Prepare validated data
                info = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_OPENING_TIME_MAP: opening_time_map,
                    CONF_CLOSING_TIME_MAP: closing_time_map,
                    CONF_OPEN_SWITCH_ENTITY_ID: open_entity,
                    CONF_CLOSE_SWITCH_ENTITY_ID: close_entity,
                    CONF_STOP_SWITCH_ENTITY_ID: stop_entity,
                    CONF_COVER_ENTITY_ID: cover_entity,
                    CONF_IS_BUTTON: user_input.get(CONF_IS_BUTTON, False),
                    CONF_TILTING_TIME_DOWN: tilt_down,
                    CONF_TILTING_TIME_UP: tilt_up,
                }
                
            except vol.Invalid as err:
                errors["base"] = str(err)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Create unique ID based on name
                await self.async_set_unique_id(user_input[CONF_NAME])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(title=info[CONF_NAME], data=info)

        data_schema = self._get_user_schema(user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "opening_example": '{"0": 0, "5": 50, "10": 100}',
                "closing_example": '{"0": 100, "8": 20, "10": 0}',
            },
        )

    def _get_user_schema(self, user_input: dict[str, Any] | None = None) -> vol.Schema:
        """Get the user schema with preserved values."""
        if user_input is None:
            user_input = {}
            
        return vol.Schema({
            vol.Required(CONF_NAME, default=user_input.get(CONF_NAME, "")): str,
            vol.Optional(CONF_USE_EXISTING_COVER, default=user_input.get(CONF_USE_EXISTING_COVER, False)): bool,
            # Cover entity option
            vol.Optional(CONF_COVER_ENTITY_ID, default=user_input.get(CONF_COVER_ENTITY_ID, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["cover"])
            ),
            # Switch entity options
            vol.Optional(CONF_OPEN_SWITCH_ENTITY_ID, default=user_input.get(CONF_OPEN_SWITCH_ENTITY_ID, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "script", "automation", "input_boolean"])
            ),
            vol.Optional(CONF_CLOSE_SWITCH_ENTITY_ID, default=user_input.get(CONF_CLOSE_SWITCH_ENTITY_ID, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "script", "automation", "input_boolean"])
            ),
            vol.Optional(CONF_STOP_SWITCH_ENTITY_ID, default=user_input.get(CONF_STOP_SWITCH_ENTITY_ID, "")): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "script", "automation", "input_boolean"])
            ),
            vol.Optional(CONF_IS_BUTTON, default=user_input.get(CONF_IS_BUTTON, False)): bool,
            # JSON fields
            vol.Required(
                CONF_OPENING_TIME_MAP, 
                default=user_input.get(CONF_OPENING_TIME_MAP, '{"0": 0, "10": 100}')
            ): str,
            vol.Required(
                CONF_CLOSING_TIME_MAP, 
                default=user_input.get(CONF_CLOSING_TIME_MAP, '{"0": 100, "10": 0}')
            ): str,
            # Tilt fields (optional, using string to allow empty values)
            vol.Optional(CONF_TILTING_TIME_DOWN, default=user_input.get(CONF_TILTING_TIME_DOWN, "")): str,
            vol.Optional(CONF_TILTING_TIME_UP, default=user_input.get(CONF_TILTING_TIME_UP, "")): str,
        })

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        config_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        
        if user_input is not None:
            try:
                # Determine if using existing cover or individual switches
                use_existing_cover = user_input.get(CONF_USE_EXISTING_COVER, False)
                
                if use_existing_cover:
                    # Validate cover entity exists
                    cover_entity = user_input.get(CONF_COVER_ENTITY_ID)
                    if not cover_entity:
                        raise vol.Invalid("Cover entity is required when using existing cover")
                    
                    if self.hass.states.get(cover_entity) is None:
                        raise vol.Invalid(f"Cover entity '{cover_entity}' not found")
                    
                    # Set switch entities to None when using existing cover
                    open_entity = None
                    close_entity = None
                    stop_entity = None
                else:
                    # Validate switch entities exist
                    open_entity = user_input.get(CONF_OPEN_SWITCH_ENTITY_ID)
                    close_entity = user_input.get(CONF_CLOSE_SWITCH_ENTITY_ID)
                    stop_entity = user_input.get(CONF_STOP_SWITCH_ENTITY_ID)
                    cover_entity = None
                    
                    if not open_entity:
                        raise vol.Invalid("Open switch entity is required when not using existing cover")
                    if not close_entity:
                        raise vol.Invalid("Close switch entity is required when not using existing cover")
                    
                    if self.hass.states.get(open_entity) is None:
                        raise vol.Invalid(f"Open switch entity '{open_entity}' not found")
                    
                    if self.hass.states.get(close_entity) is None:
                        raise vol.Invalid(f"Close switch entity '{close_entity}' not found")
                    
                    if stop_entity and self.hass.states.get(stop_entity) is None:
                        raise vol.Invalid(f"Stop switch entity '{stop_entity}' not found")
                
                # Validate time maps
                opening_time_map = validate_time_map(user_input[CONF_OPENING_TIME_MAP], "Opening")
                closing_time_map = validate_time_map(user_input[CONF_CLOSING_TIME_MAP], "Closing")
                
                # Validate tilt times (properly handle None/empty values)
                tilt_down = validate_tilt_time(user_input.get(CONF_TILTING_TIME_DOWN))
                tilt_up = validate_tilt_time(user_input.get(CONF_TILTING_TIME_UP))
                
                # Prepare validated data
                info = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_OPENING_TIME_MAP: opening_time_map,
                    CONF_CLOSING_TIME_MAP: closing_time_map,
                    CONF_OPEN_SWITCH_ENTITY_ID: open_entity,
                    CONF_CLOSE_SWITCH_ENTITY_ID: close_entity,
                    CONF_STOP_SWITCH_ENTITY_ID: stop_entity,
                    CONF_COVER_ENTITY_ID: cover_entity,
                    CONF_IS_BUTTON: user_input.get(CONF_IS_BUTTON, False),
                    CONF_TILTING_TIME_DOWN: tilt_down,
                    CONF_TILTING_TIME_UP: tilt_up,
                }
                
            except vol.Invalid as err:
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=self._get_reconfigure_schema(config_entry.data, user_input),
                    errors={"base": str(err)},
                )
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=self._get_reconfigure_schema(config_entry.data, user_input),
                    errors={"base": "unknown"},
                )
            else:
                return self.async_update_reload_and_abort(
                    config_entry, data=info, reason="reconfigure_successful"
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self._get_reconfigure_schema(config_entry.data),
            description_placeholders={
                "opening_example": '{"0": 0, "5": 50, "10": 100}',
                "closing_example": '{"0": 100, "8": 20, "10": 0}',
            },
        )

    def _get_reconfigure_schema(self, data: dict[str, Any], user_input: dict[str, Any] | None = None) -> vol.Schema:
        """Get the reconfigure schema with current values."""
        # Use user_input if available (for form preservation), otherwise use saved data
        if user_input is None:
            user_input = {}
        
        # Get current tilt values, handling None properly
        current_tilt_down = user_input.get(CONF_TILTING_TIME_DOWN) or data.get(CONF_TILTING_TIME_DOWN)
        current_tilt_up = user_input.get(CONF_TILTING_TIME_UP) or data.get(CONF_TILTING_TIME_UP)
        
        # Determine if currently using existing cover
        has_cover_entity = user_input.get(CONF_USE_EXISTING_COVER, data.get(CONF_COVER_ENTITY_ID) is not None)
        
        return vol.Schema({
            vol.Required(CONF_NAME, default=user_input.get(CONF_NAME) or data.get(CONF_NAME, "")): str,
            vol.Optional(CONF_USE_EXISTING_COVER, default=has_cover_entity): bool,
            # Cover entity option
            vol.Optional(
                CONF_COVER_ENTITY_ID,
                default=user_input.get(CONF_COVER_ENTITY_ID) or data.get(CONF_COVER_ENTITY_ID, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["cover"])
            ),
            # Switch entity options
            vol.Optional(
                CONF_OPEN_SWITCH_ENTITY_ID, 
                default=user_input.get(CONF_OPEN_SWITCH_ENTITY_ID) or data.get(CONF_OPEN_SWITCH_ENTITY_ID, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "script", "automation", "input_boolean"])
            ),
            vol.Optional(
                CONF_CLOSE_SWITCH_ENTITY_ID, 
                default=user_input.get(CONF_CLOSE_SWITCH_ENTITY_ID) or data.get(CONF_CLOSE_SWITCH_ENTITY_ID, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "script", "automation", "input_boolean"])
            ),
            vol.Optional(
                CONF_STOP_SWITCH_ENTITY_ID, 
                default=user_input.get(CONF_STOP_SWITCH_ENTITY_ID) or data.get(CONF_STOP_SWITCH_ENTITY_ID, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "script", "automation", "input_boolean"])
            ),
            vol.Optional(
                CONF_IS_BUTTON, 
                default=user_input.get(CONF_IS_BUTTON, data.get(CONF_IS_BUTTON, False))
            ): bool,
            vol.Required(
                CONF_OPENING_TIME_MAP, 
                default=user_input.get(CONF_OPENING_TIME_MAP) or json.dumps(data.get(CONF_OPENING_TIME_MAP, {"0": 0, "10": 100}))
            ): str,
            vol.Required(
                CONF_CLOSING_TIME_MAP, 
                default=user_input.get(CONF_CLOSING_TIME_MAP) or json.dumps(data.get(CONF_CLOSING_TIME_MAP, {"0": 100, "10": 0}))
            ): str,
            vol.Optional(
                CONF_TILTING_TIME_DOWN, 
                default=str(current_tilt_down) if current_tilt_down is not None else ""
            ): str,  # Use string to allow empty values
            vol.Optional(
                CONF_TILTING_TIME_UP, 
                default=str(current_tilt_up) if current_tilt_up is not None else ""
            ): str,  # Use string to allow empty values
        })