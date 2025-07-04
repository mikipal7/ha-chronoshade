"""Config flow for Cover Time Based integration."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_OPENING_TIME_MAP,
    CONF_CLOSING_TIME_MAP,
    CONF_OPENING_TIME,
    CONF_CLOSING_TIME,
    CONF_TILTING_TIME_DOWN,
    CONF_TILTING_TIME_UP,
    CONF_OPEN_SWITCH_ENTITY_ID,
    CONF_CLOSE_SWITCH_ENTITY_ID,
    CONF_STOP_SWITCH_ENTITY_ID,
    CONF_IS_BUTTON,
    CONF_COVER_ENTITY_ID,
    CONF_CONTROL_METHOD,
    CONTROL_METHOD_SWITCHES,
    CONTROL_METHOD_EXISTING_COVER,
    DEFAULT_OPENING_TIME_MAP,
    DEFAULT_CLOSING_TIME_MAP,
    CURRENT_CONFIG_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class TimeMapValidator:
    """Validator for time maps with comprehensive error messages."""
    
    @staticmethod
    def validate_json_format(time_map_str: str) -> dict[str, Any]:
        """Validate JSON format and return parsed data."""
        if not time_map_str or not time_map_str.strip():
            raise vol.Invalid("Time map cannot be empty")
        
        try:
            data = json.loads(time_map_str)
        except json.JSONDecodeError as err:
            raise vol.Invalid(f"Invalid JSON format: {err}") from err
        
        if not isinstance(data, dict):
            raise vol.Invalid("Time map must be a JSON object (dictionary)")
        
        if not data:
            raise vol.Invalid("Time map cannot be empty")
        
        return data
    
    @staticmethod
    def validate_time_position_pairs(data: dict[str, Any]) -> dict[float, int]:
        """Validate and convert time-position pairs."""
        time_map = {}
        
        for time_str, position in data.items():
            # Validate time
            try:
                time_val = float(time_str)
                if time_val < 0:
                    raise vol.Invalid(f"Time '{time_str}' must be non-negative")
            except (ValueError, TypeError) as err:
                raise vol.Invalid(f"Invalid time value '{time_str}': must be a number") from err
            
            # Validate position
            try:
                pos_val = int(position)
                if not 0 <= pos_val <= 100:
                    raise vol.Invalid(f"Position {pos_val} at time {time_val} must be between 0 and 100")
            except (ValueError, TypeError) as err:
                raise vol.Invalid(f"Invalid position value '{position}' at time {time_val}: must be an integer") from err
            
            time_map[time_val] = pos_val
        
        return time_map
    
    @staticmethod
    def validate_time_sequence(time_map: dict[float, int], map_type: str) -> None:
        """Validate time sequence and position progression."""
        if not time_map:
            raise vol.Invalid(f"{map_type} time map cannot be empty")
        
        # Sort by time
        sorted_times = sorted(time_map.keys())
        positions = [time_map[t] for t in sorted_times]
        
        # Must start at time 0
        if sorted_times[0] != 0:
            raise vol.Invalid(f"{map_type} time map must start at time 0 (found {sorted_times[0]})")
        
        # Validate start/end positions based on map type
        if map_type.lower() == "opening":
            if positions[0] != 0:
                raise vol.Invalid(f"Opening time map must start at position 0 (closed), found {positions[0]}")
            if positions[-1] != 100:
                raise vol.Invalid(f"Opening time map must end at position 100 (open), found {positions[-1]}")
            
            # Validate monotonic increasing
            for i in range(1, len(positions)):
                if positions[i] < positions[i-1]:
                    raise vol.Invalid(
                        f"Opening time map positions must be non-decreasing. "
                        f"Position {positions[i]} at time {sorted_times[i]} is less than "
                        f"position {positions[i-1]} at time {sorted_times[i-1]}"
                    )
        
        elif map_type.lower() == "closing":
            if positions[0] != 100:
                raise vol.Invalid(f"Closing time map must start at position 100 (open), found {positions[0]}")
            if positions[-1] != 0:
                raise vol.Invalid(f"Closing time map must end at position 0 (closed), found {positions[-1]}")
            
            # Validate monotonic decreasing
            for i in range(1, len(positions)):
                if positions[i] > positions[i-1]:
                    raise vol.Invalid(
                        f"Closing time map positions must be non-increasing. "
                        f"Position {positions[i]} at time {sorted_times[i]} is greater than "
                        f"position {positions[i-1]} at time {sorted_times[i-1]}"
                    )
    
    @classmethod
    def validate_time_map(cls, time_map_str: str, map_type: str) -> dict[float, int]:
        """Complete validation of time map."""
        # Step 1: Validate JSON format
        data = cls.validate_json_format(time_map_str)
        
        # Step 2: Validate time-position pairs
        time_map = cls.validate_time_position_pairs(data)
        
        # Step 3: Validate sequence and progression
        cls.validate_time_sequence(time_map, map_type)
        
        return time_map


def validate_tilt_time(value: Any) -> float | None:
    """Validate tilt time value."""
    if value is None or value == "" or value == 0:
        return None
    
    try:
        float_val = float(value)
        if float_val <= 0:
            raise vol.Invalid("Tilt time must be positive")
        if float_val > 300:
            raise vol.Invalid("Tilt time cannot exceed 300 seconds")
        return float_val
    except (ValueError, TypeError) as err:
        raise vol.Invalid(f"Invalid tilt time: {err}") from err


def generate_unique_id(name: str) -> str:
    """Generate a stable unique ID from name."""
    return re.sub(r'[^a-z0-9_]', '_', name.lower().strip())


def format_time_map_for_ui(time_map: dict[float, int] | dict[str, int] | dict) -> str:
    """Format time map for UI display with proper JSON formatting."""
    if not time_map:
        return "{}"
    
    # Handle both float and string keys
    string_map = {}
    for key, value in time_map.items():
        # Convert key to string if it's not already
        str_key = str(key) if not isinstance(key, str) else key
        string_map[str_key] = value
    
    return json.dumps(string_map, sort_keys=True)


def create_linear_time_map(total_time: float, start_position: int, end_position: int) -> dict[float, int]:
    """Create a linear time map from start to end position over total time."""
    return {0.0: start_position, total_time: end_position}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cover Time Based."""

    VERSION = CURRENT_CONFIG_VERSION

    def __init__(self) -> None:
        """Initialize config flow."""
        self._control_method: str | None = None
        self._name: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - choose control method."""
        if user_input is not None:
            self._control_method = user_input[CONF_CONTROL_METHOD]
            
            if self._control_method == CONTROL_METHOD_SWITCHES:
                return await self.async_step_switches()
            else:
                return await self.async_step_existing_cover()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CONTROL_METHOD): vol.In({
                    CONTROL_METHOD_SWITCHES: "Individual switch entities (open/close/stop)",
                    CONTROL_METHOD_EXISTING_COVER: "Existing cover entity"
                })
            }),
        )

    async def async_step_switches(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure cover using individual switch entities - choose configuration mode."""
        if user_input is not None:
            config_mode = user_input["config_mode"]
            
            if config_mode == "standard":
                return await self.async_step_switches_standard()
            elif config_mode == "advanced":
                return await self.async_step_switches_advanced()
            else:  # automatic
                return await self.async_step_switches_automatic()

        return self.async_show_form(
            step_id="switches",
            data_schema=vol.Schema({
                vol.Required("config_mode"): vol.In({
                    "standard": "Standard - Simple time and position setup",
                    "advanced": "Advanced - Full JSON time maps",
                    "automatic": "Automatic - Quick setup with detection"
                })
            }),
        )

    async def async_step_switches_standard(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure cover using standard mode."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate required entities
                open_entity = user_input[CONF_OPEN_SWITCH_ENTITY_ID]
                close_entity = user_input[CONF_CLOSE_SWITCH_ENTITY_ID]
                stop_entity = user_input.get(CONF_STOP_SWITCH_ENTITY_ID)
                
                # Check entities exist
                if self.hass.states.get(open_entity) is None:
                    raise vol.Invalid(f"Open entity '{open_entity}' not found")
                if self.hass.states.get(close_entity) is None:
                    raise vol.Invalid(f"Close entity '{close_entity}' not found")
                if stop_entity and self.hass.states.get(stop_entity) is None:
                    raise vol.Invalid(f"Stop entity '{stop_entity}' not found")
                
                # Create simple time maps from user input
                opening_time = float(user_input[CONF_OPENING_TIME])
                closing_time = float(user_input[CONF_CLOSING_TIME])
                
                opening_map = create_linear_time_map(opening_time, 0, 100)
                closing_map = create_linear_time_map(closing_time, 100, 0)
                
                # Validate tilt times
                tilt_down = validate_tilt_time(user_input.get(CONF_TILTING_TIME_DOWN))
                tilt_up = validate_tilt_time(user_input.get(CONF_TILTING_TIME_UP))
                
                # Check for existing entry with same name
                name = user_input[CONF_NAME]
                unique_id = generate_unique_id(name)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                
                # Create entry
                data = {
                    CONF_NAME: name,
                    CONF_CONTROL_METHOD: CONTROL_METHOD_SWITCHES,
                    CONF_OPEN_SWITCH_ENTITY_ID: open_entity,
                    CONF_CLOSE_SWITCH_ENTITY_ID: close_entity,
                    CONF_STOP_SWITCH_ENTITY_ID: stop_entity,
                    CONF_IS_BUTTON: user_input.get(CONF_IS_BUTTON, False),
                    CONF_OPENING_TIME_MAP: opening_map,
                    CONF_CLOSING_TIME_MAP: closing_map,
                    CONF_TILTING_TIME_DOWN: tilt_down,
                    CONF_TILTING_TIME_UP: tilt_up,
                }
                
                return self.async_create_entry(title=name, data=data)
                
            except vol.Invalid as err:
                errors["base"] = str(err)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error in standard switches config")
                errors["base"] = f"unexpected_error: {err}"

        return self.async_show_form(
            step_id="switches_standard",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_OPEN_SWITCH_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "script", "automation", "input_boolean", "button"]
                    )
                ),
                vol.Required(CONF_CLOSE_SWITCH_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "script", "automation", "input_boolean", "button"]
                    )
                ),
                vol.Optional(CONF_STOP_SWITCH_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "script", "automation", "input_boolean", "button"]
                    )
                ),
                vol.Optional(CONF_IS_BUTTON, default=False): bool,
                vol.Required(CONF_OPENING_TIME, default=10.0): vol.All(
                    vol.Coerce(float), vol.Range(min=0.1, max=300)
                ),
                vol.Required(CONF_CLOSING_TIME, default=10.0): vol.All(
                    vol.Coerce(float), vol.Range(min=0.1, max=300)
                ),
                vol.Optional(CONF_TILTING_TIME_DOWN): str,
                vol.Optional(CONF_TILTING_TIME_UP): str,
            }),
            errors=errors,
        )

    async def async_step_switches_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure cover using advanced mode."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate required entities
                open_entity = user_input[CONF_OPEN_SWITCH_ENTITY_ID]
                close_entity = user_input[CONF_CLOSE_SWITCH_ENTITY_ID]
                stop_entity = user_input.get(CONF_STOP_SWITCH_ENTITY_ID)
                
                # Check entities exist
                if self.hass.states.get(open_entity) is None:
                    raise vol.Invalid(f"Open entity '{open_entity}' not found")
                if self.hass.states.get(close_entity) is None:
                    raise vol.Invalid(f"Close entity '{close_entity}' not found")
                if stop_entity and self.hass.states.get(stop_entity) is None:
                    raise vol.Invalid(f"Stop entity '{stop_entity}' not found")
                
                # Validate time maps
                opening_map = TimeMapValidator.validate_time_map(
                    user_input[CONF_OPENING_TIME_MAP], "Opening"
                )
                closing_map = TimeMapValidator.validate_time_map(
                    user_input[CONF_CLOSING_TIME_MAP], "Closing"
                )
                
                # Validate tilt times
                tilt_down = validate_tilt_time(user_input.get(CONF_TILTING_TIME_DOWN))
                tilt_up = validate_tilt_time(user_input.get(CONF_TILTING_TIME_UP))
                
                # Check for existing entry with same name
                name = user_input[CONF_NAME]
                unique_id = generate_unique_id(name)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                
                # Create entry
                data = {
                    CONF_NAME: name,
                    CONF_CONTROL_METHOD: CONTROL_METHOD_SWITCHES,
                    CONF_OPEN_SWITCH_ENTITY_ID: open_entity,
                    CONF_CLOSE_SWITCH_ENTITY_ID: close_entity,
                    CONF_STOP_SWITCH_ENTITY_ID: stop_entity,
                    CONF_IS_BUTTON: user_input.get(CONF_IS_BUTTON, False),
                    CONF_OPENING_TIME_MAP: opening_map,
                    CONF_CLOSING_TIME_MAP: closing_map,
                    CONF_TILTING_TIME_DOWN: tilt_down,
                    CONF_TILTING_TIME_UP: tilt_up,
                }
                
                return self.async_create_entry(title=name, data=data)
                
            except vol.Invalid as err:
                errors["base"] = str(err)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error in advanced switches config")
                errors["base"] = f"unexpected_error: {err}"

        return self.async_show_form(
            step_id="switches_advanced",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_OPEN_SWITCH_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "script", "automation", "input_boolean", "button"]
                    )
                ),
                vol.Required(CONF_CLOSE_SWITCH_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "script", "automation", "input_boolean", "button"]
                    )
                ),
                vol.Optional(CONF_STOP_SWITCH_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "script", "automation", "input_boolean", "button"]
                    )
                ),
                vol.Optional(CONF_IS_BUTTON, default=False): bool,
                vol.Required(
                    CONF_OPENING_TIME_MAP,
                    default=format_time_map_for_ui(DEFAULT_OPENING_TIME_MAP)
                ): str,
                vol.Required(
                    CONF_CLOSING_TIME_MAP,
                    default=format_time_map_for_ui(DEFAULT_CLOSING_TIME_MAP)
                ): str,
                vol.Optional(CONF_TILTING_TIME_DOWN): str,
                vol.Optional(CONF_TILTING_TIME_UP): str,
            }),
            errors=errors,
        )

    async def async_step_switches_automatic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure cover using automatic mode."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate required entities
                open_entity = user_input[CONF_OPEN_SWITCH_ENTITY_ID]
                close_entity = user_input[CONF_CLOSE_SWITCH_ENTITY_ID]
                stop_entity = user_input.get(CONF_STOP_SWITCH_ENTITY_ID)
                
                # Check entities exist
                if self.hass.states.get(open_entity) is None:
                    raise vol.Invalid(f"Open entity '{open_entity}' not found")
                if self.hass.states.get(close_entity) is None:
                    raise vol.Invalid(f"Close entity '{close_entity}' not found")
                if stop_entity and self.hass.states.get(stop_entity) is None:
                    raise vol.Invalid(f"Stop entity '{stop_entity}' not found")
                
                # Auto-detect entity types and set defaults
                open_state = self.hass.states.get(open_entity)
                is_button = self._detect_button_entity(open_state)
                
                # Use default time maps for automatic setup
                opening_map = DEFAULT_OPENING_TIME_MAP.copy()
                closing_map = DEFAULT_CLOSING_TIME_MAP.copy()
                
                # Check for existing entry with same name
                name = user_input[CONF_NAME]
                unique_id = generate_unique_id(name)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                
                # Create entry
                data = {
                    CONF_NAME: name,
                    CONF_CONTROL_METHOD: CONTROL_METHOD_SWITCHES,
                    CONF_OPEN_SWITCH_ENTITY_ID: open_entity,
                    CONF_CLOSE_SWITCH_ENTITY_ID: close_entity,
                    CONF_STOP_SWITCH_ENTITY_ID: stop_entity,
                    CONF_IS_BUTTON: is_button,
                    CONF_OPENING_TIME_MAP: opening_map,
                    CONF_CLOSING_TIME_MAP: closing_map,
                    CONF_TILTING_TIME_DOWN: None,
                    CONF_TILTING_TIME_UP: None,
                }
                
                return self.async_create_entry(title=name, data=data)
                
            except vol.Invalid as err:
                errors["base"] = str(err)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error in automatic switches config")
                errors["base"] = f"unexpected_error: {err}"

        return self.async_show_form(
            step_id="switches_automatic",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_OPEN_SWITCH_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "script", "automation", "input_boolean", "button"]
                    )
                ),
                vol.Required(CONF_CLOSE_SWITCH_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "script", "automation", "input_boolean", "button"]
                    )
                ),
                vol.Optional(CONF_STOP_SWITCH_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "script", "automation", "input_boolean", "button"]
                    )
                ),
            }),
            errors=errors,
        )

    def _detect_button_entity(self, entity_state) -> bool:
        """Detect if entity is a button type."""
        if not entity_state:
            return False
        
        entity_id = entity_state.entity_id
        domain = entity_id.split(".")[0]
        
        # Button domain entities are always momentary
        if domain == "button":
            return True
        
        # Check for common button patterns in entity names
        button_patterns = ["button", "press", "push", "momentary"]
        entity_name = entity_state.attributes.get("friendly_name", entity_id).lower()
        
        return any(pattern in entity_name for pattern in button_patterns)

    async def async_step_existing_cover(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure cover using existing cover entity - choose configuration mode."""
        if user_input is not None:
            config_mode = user_input["config_mode"]
            
            if config_mode == "standard":
                return await self.async_step_existing_cover_standard()
            elif config_mode == "advanced":
                return await self.async_step_existing_cover_advanced()
            else:  # automatic
                return await self.async_step_existing_cover_automatic()

        return self.async_show_form(
            step_id="existing_cover",
            data_schema=vol.Schema({
                vol.Required("config_mode"): vol.In({
                    "standard": "Standard - Simple time and position setup",
                    "advanced": "Advanced - Full JSON time maps",
                    "automatic": "Automatic - Quick setup with defaults"
                })
            }),
        )

    async def async_step_existing_cover_standard(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure existing cover using standard mode."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate cover entity
                cover_entity = user_input[CONF_COVER_ENTITY_ID]
                if self.hass.states.get(cover_entity) is None:
                    raise vol.Invalid(f"Cover entity '{cover_entity}' not found")
                
                # Create simple time maps from user input
                opening_time = float(user_input[CONF_OPENING_TIME])
                closing_time = float(user_input[CONF_CLOSING_TIME])
                
                opening_map = create_linear_time_map(opening_time, 0, 100)
                closing_map = create_linear_time_map(closing_time, 100, 0)
                
                # Validate tilt times
                tilt_down = validate_tilt_time(user_input.get(CONF_TILTING_TIME_DOWN))
                tilt_up = validate_tilt_time(user_input.get(CONF_TILTING_TIME_UP))
                
                # Check for existing entry with same name
                name = user_input[CONF_NAME]
                unique_id = generate_unique_id(name)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                
                # Create entry
                data = {
                    CONF_NAME: name,
                    CONF_CONTROL_METHOD: CONTROL_METHOD_EXISTING_COVER,
                    CONF_COVER_ENTITY_ID: cover_entity,
                    CONF_OPENING_TIME_MAP: opening_map,
                    CONF_CLOSING_TIME_MAP: closing_map,
                    CONF_TILTING_TIME_DOWN: tilt_down,
                    CONF_TILTING_TIME_UP: tilt_up,
                }
                
                return self.async_create_entry(title=name, data=data)
                
            except vol.Invalid as err:
                errors["base"] = str(err)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error in standard existing cover config")
                errors["base"] = f"unexpected_error: {err}"

        return self.async_show_form(
            step_id="existing_cover_standard",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_COVER_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["cover"])
                ),
                vol.Required(CONF_OPENING_TIME, default=10.0): vol.All(
                    vol.Coerce(float), vol.Range(min=0.1, max=300)
                ),
                vol.Required(CONF_CLOSING_TIME, default=10.0): vol.All(
                    vol.Coerce(float), vol.Range(min=0.1, max=300)
                ),
                vol.Optional(CONF_TILTING_TIME_DOWN): str,
                vol.Optional(CONF_TILTING_TIME_UP): str,
            }),
            errors=errors,
        )

    async def async_step_existing_cover_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure existing cover using advanced mode."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate cover entity
                cover_entity = user_input[CONF_COVER_ENTITY_ID]
                if self.hass.states.get(cover_entity) is None:
                    raise vol.Invalid(f"Cover entity '{cover_entity}' not found")
                
                # Validate time maps
                opening_map = TimeMapValidator.validate_time_map(
                    user_input[CONF_OPENING_TIME_MAP], "Opening"
                )
                closing_map = TimeMapValidator.validate_time_map(
                    user_input[CONF_CLOSING_TIME_MAP], "Closing"
                )
                
                # Validate tilt times
                tilt_down = validate_tilt_time(user_input.get(CONF_TILTING_TIME_DOWN))
                tilt_up = validate_tilt_time(user_input.get(CONF_TILTING_TIME_UP))
                
                # Check for existing entry with same name
                name = user_input[CONF_NAME]
                unique_id = generate_unique_id(name)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                
                # Create entry
                data = {
                    CONF_NAME: name,
                    CONF_CONTROL_METHOD: CONTROL_METHOD_EXISTING_COVER,
                    CONF_COVER_ENTITY_ID: cover_entity,
                    CONF_OPENING_TIME_MAP: opening_map,
                    CONF_CLOSING_TIME_MAP: closing_map,
                    CONF_TILTING_TIME_DOWN: tilt_down,
                    CONF_TILTING_TIME_UP: tilt_up,
                }
                
                return self.async_create_entry(title=name, data=data)
                
            except vol.Invalid as err:
                errors["base"] = str(err)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error in advanced existing cover config")
                errors["base"] = f"unexpected_error: {err}"

        return self.async_show_form(
            step_id="existing_cover_advanced",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_COVER_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["cover"])
                ),
                vol.Required(
                    CONF_OPENING_TIME_MAP,
                    default=format_time_map_for_ui(DEFAULT_OPENING_TIME_MAP)
                ): str,
                vol.Required(
                    CONF_CLOSING_TIME_MAP,
                    default=format_time_map_for_ui(DEFAULT_CLOSING_TIME_MAP)
                ): str,
                vol.Optional(CONF_TILTING_TIME_DOWN): str,
                vol.Optional(CONF_TILTING_TIME_UP): str,
            }),
            errors=errors,
        )

    async def async_step_existing_cover_automatic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure existing cover using automatic mode."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate cover entity
                cover_entity = user_input[CONF_COVER_ENTITY_ID]
                if self.hass.states.get(cover_entity) is None:
                    raise vol.Invalid(f"Cover entity '{cover_entity}' not found")
                
                # Use default time maps for automatic setup
                opening_map = DEFAULT_OPENING_TIME_MAP.copy()
                closing_map = DEFAULT_CLOSING_TIME_MAP.copy()
                
                # Check for existing entry with same name
                name = user_input[CONF_NAME]
                unique_id = generate_unique_id(name)
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                
                # Create entry
                data = {
                    CONF_NAME: name,
                    CONF_CONTROL_METHOD: CONTROL_METHOD_EXISTING_COVER,
                    CONF_COVER_ENTITY_ID: cover_entity,
                    CONF_OPENING_TIME_MAP: opening_map,
                    CONF_CLOSING_TIME_MAP: closing_map,
                    CONF_TILTING_TIME_DOWN: None,
                    CONF_TILTING_TIME_UP: None,
                }
                
                return self.async_create_entry(title=name, data=data)
                
            except vol.Invalid as err:
                errors["base"] = str(err)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error in automatic existing cover config")
                errors["base"] = f"unexpected_error: {err}"

        return self.async_show_form(
            step_id="existing_cover_automatic",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_COVER_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["cover"])
                ),
            }),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration."""
        config_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if not config_entry:
            return self.async_abort(reason="entry_not_found")
        
        current_data = config_entry.data
        control_method = current_data.get(CONF_CONTROL_METHOD, CONTROL_METHOD_SWITCHES)
        
        if control_method == CONTROL_METHOD_SWITCHES:
            return await self.async_step_reconfigure_switches(user_input)
        else:
            return await self.async_step_reconfigure_existing_cover(user_input)

    async def async_step_reconfigure_switches(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration for switch-based covers."""
        config_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        current_data = config_entry.data
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate entities
                open_entity = user_input[CONF_OPEN_SWITCH_ENTITY_ID]
                close_entity = user_input[CONF_CLOSE_SWITCH_ENTITY_ID]
                stop_entity = user_input.get(CONF_STOP_SWITCH_ENTITY_ID)
                
                if self.hass.states.get(open_entity) is None:
                    raise vol.Invalid(f"Open entity '{open_entity}' not found")
                if self.hass.states.get(close_entity) is None:
                    raise vol.Invalid(f"Close entity '{close_entity}' not found")
                if stop_entity and self.hass.states.get(stop_entity) is None:
                    raise vol.Invalid(f"Stop entity '{stop_entity}' not found")
                
                # Validate time maps
                opening_map = TimeMapValidator.validate_time_map(
                    user_input[CONF_OPENING_TIME_MAP], "Opening"
                )
                closing_map = TimeMapValidator.validate_time_map(
                    user_input[CONF_CLOSING_TIME_MAP], "Closing"
                )
                
                # Validate tilt times
                tilt_down = validate_tilt_time(user_input.get(CONF_TILTING_TIME_DOWN))
                tilt_up = validate_tilt_time(user_input.get(CONF_TILTING_TIME_UP))
                
                # Update entry
                new_data = {
                    **current_data,
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_OPEN_SWITCH_ENTITY_ID: open_entity,
                    CONF_CLOSE_SWITCH_ENTITY_ID: close_entity,
                    CONF_STOP_SWITCH_ENTITY_ID: stop_entity,
                    CONF_IS_BUTTON: user_input.get(CONF_IS_BUTTON, False),
                    CONF_OPENING_TIME_MAP: opening_map,
                    CONF_CLOSING_TIME_MAP: closing_map,
                    CONF_TILTING_TIME_DOWN: tilt_down,
                    CONF_TILTING_TIME_UP: tilt_up,
                }
                
                self.hass.config_entries.async_update_entry(config_entry, data=new_data)
                return self.async_abort(reason="reconfigure_successful")
                
            except vol.Invalid as err:
                errors["base"] = str(err)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error in reconfigure switches")
                errors["base"] = f"unexpected_error: {err}"

        return self.async_show_form(
            step_id="reconfigure_switches",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=current_data.get(CONF_NAME, "")): str,
                vol.Required(
                    CONF_OPEN_SWITCH_ENTITY_ID,
                    default=current_data.get(CONF_OPEN_SWITCH_ENTITY_ID, "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "script", "automation", "input_boolean", "button"]
                    )
                ),
                vol.Required(
                    CONF_CLOSE_SWITCH_ENTITY_ID,
                    default=current_data.get(CONF_CLOSE_SWITCH_ENTITY_ID, "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "script", "automation", "input_boolean", "button"]
                    )
                ),
                vol.Optional(
                    CONF_STOP_SWITCH_ENTITY_ID,
                    default=current_data.get(CONF_STOP_SWITCH_ENTITY_ID)
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "script", "automation", "input_boolean", "button"]
                    )
                ),
                vol.Optional(
                    CONF_IS_BUTTON,
                    default=current_data.get(CONF_IS_BUTTON, False)
                ): bool,
                vol.Required(
                    CONF_OPENING_TIME_MAP,
                    default=format_time_map_for_ui(current_data.get(CONF_OPENING_TIME_MAP, DEFAULT_OPENING_TIME_MAP))
                ): str,
                vol.Required(
                    CONF_CLOSING_TIME_MAP,
                    default=format_time_map_for_ui(current_data.get(CONF_CLOSING_TIME_MAP, DEFAULT_CLOSING_TIME_MAP))
                ): str,
                vol.Optional(
                    CONF_TILTING_TIME_DOWN,
                    default=str(current_data.get(CONF_TILTING_TIME_DOWN, "")) if current_data.get(CONF_TILTING_TIME_DOWN) else ""
                ): str,
                vol.Optional(
                    CONF_TILTING_TIME_UP,
                    default=str(current_data.get(CONF_TILTING_TIME_UP, "")) if current_data.get(CONF_TILTING_TIME_UP) else ""
                ): str,
            }),
            errors=errors,
        )

    async def async_step_reconfigure_existing_cover(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration for existing cover."""
        config_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        current_data = config_entry.data
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate cover entity
                cover_entity = user_input[CONF_COVER_ENTITY_ID]
                if self.hass.states.get(cover_entity) is None:
                    raise vol.Invalid(f"Cover entity '{cover_entity}' not found")
                
                # Validate time maps
                opening_map = TimeMapValidator.validate_time_map(
                    user_input[CONF_OPENING_TIME_MAP], "Opening"
                )
                closing_map = TimeMapValidator.validate_time_map(
                    user_input[CONF_CLOSING_TIME_MAP], "Closing"
                )
                
                # Validate tilt times
                tilt_down = validate_tilt_time(user_input.get(CONF_TILTING_TIME_DOWN))
                tilt_up = validate_tilt_time(user_input.get(CONF_TILTING_TIME_UP))
                
                # Update entry
                new_data = {
                    **current_data,
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_COVER_ENTITY_ID: cover_entity,
                    CONF_OPENING_TIME_MAP: opening_map,
                    CONF_CLOSING_TIME_MAP: closing_map,
                    CONF_TILTING_TIME_DOWN: tilt_down,
                    CONF_TILTING_TIME_UP: tilt_up,
                }
                
                self.hass.config_entries.async_update_entry(config_entry, data=new_data)
                return self.async_abort(reason="reconfigure_successful")
                
            except vol.Invalid as err:
                errors["base"] = str(err)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error in reconfigure existing cover")
                errors["base"] = f"unexpected_error: {err}"

        return self.async_show_form(
            step_id="reconfigure_existing_cover",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=current_data.get(CONF_NAME, "")): str,
                vol.Required(
                    CONF_COVER_ENTITY_ID,
                    default=current_data.get(CONF_COVER_ENTITY_ID, "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["cover"])
                ),
                vol.Required(
                    CONF_OPENING_TIME_MAP,
                    default=format_time_map_for_ui(current_data.get(CONF_OPENING_TIME_MAP, DEFAULT_OPENING_TIME_MAP))
                ): str,
                vol.Required(
                    CONF_CLOSING_TIME_MAP,
                    default=format_time_map_for_ui(current_data.get(CONF_CLOSING_TIME_MAP, DEFAULT_CLOSING_TIME_MAP))
                ): str,
                vol.Optional(
                    CONF_TILTING_TIME_DOWN,
                    default=str(current_data.get(CONF_TILTING_TIME_DOWN, "")) if current_data.get(CONF_TILTING_TIME_DOWN) else ""
                ): str,
                vol.Optional(
                    CONF_TILTING_TIME_UP,
                    default=str(current_data.get(CONF_TILTING_TIME_UP, "")) if current_data.get(CONF_TILTING_TIME_UP) else ""
                ): str,
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Cover Time Based."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate tilt times
                tilt_down = validate_tilt_time(user_input.get(CONF_TILTING_TIME_DOWN))
                tilt_up = validate_tilt_time(user_input.get(CONF_TILTING_TIME_UP))
                
                # Update config entry data (not options)
                new_data = {
                    **self.config_entry.data,
                    CONF_TILTING_TIME_DOWN: tilt_down,
                    CONF_TILTING_TIME_UP: tilt_up,
                }
                
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )
                
                return self.async_create_entry(title="", data={})
                
            except vol.Invalid as err:
                errors["base"] = str(err)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error in options flow")
                errors["base"] = f"unexpected_error: {err}"

        current_data = self.config_entry.data
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_TILTING_TIME_DOWN,
                    default=str(current_data.get(CONF_TILTING_TIME_DOWN, "")) if current_data.get(CONF_TILTING_TIME_DOWN) else ""
                ): str,
                vol.Optional(
                    CONF_TILTING_TIME_UP,
                    default=str(current_data.get(CONF_TILTING_TIME_UP, "")) if current_data.get(CONF_TILTING_TIME_UP) else ""
                ): str,
            }),
            errors=errors,
        )