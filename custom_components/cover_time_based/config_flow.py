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
    DEFAULT_TILT_TIME,
)

_LOGGER = logging.getLogger(__name__)


def validate_time_map(time_map_str: str, map_type: str) -> dict[float, int]:
    """Validate and parse time map from string."""
    try:
        time_map_raw = json.loads(time_map_str)
    except json.JSONDecodeError as err:
        raise vol.Invalid(f"Invalid JSON format: {err}") from err
    
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


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    
    # Validate time maps
    opening_time_map = validate_time_map(data[CONF_OPENING_TIME_MAP], "Opening")
    closing_time_map = validate_time_map(data[CONF_CLOSING_TIME_MAP], "Closing")
    
    # Validate entity IDs exist
    open_entity = data[CONF_OPEN_SWITCH_ENTITY_ID]
    close_entity = data[CONF_CLOSE_SWITCH_ENTITY_ID]
    stop_entity = data.get(CONF_STOP_SWITCH_ENTITY_ID)
    
    # Check if entities exist
    if hass.states.get(open_entity) is None:
        raise vol.Invalid(f"Open switch entity '{open_entity}' not found")
    
    if hass.states.get(close_entity) is None:
        raise vol.Invalid(f"Close switch entity '{close_entity}' not found")
    
    if stop_entity and hass.states.get(stop_entity) is None:
        raise vol.Invalid(f"Stop switch entity '{stop_entity}' not found")
    
    # Return validated data
    return {
        CONF_NAME: data[CONF_NAME],
        CONF_OPENING_TIME_MAP: opening_time_map,
        CONF_CLOSING_TIME_MAP: closing_time_map,
        CONF_OPEN_SWITCH_ENTITY_ID: open_entity,
        CONF_CLOSE_SWITCH_ENTITY_ID: close_entity,
        CONF_STOP_SWITCH_ENTITY_ID: stop_entity,
        CONF_IS_BUTTON: data.get(CONF_IS_BUTTON, False),
        CONF_TILTING_TIME_DOWN: data.get(CONF_TILTING_TIME_DOWN),
        CONF_TILTING_TIME_UP: data.get(CONF_TILTING_TIME_UP),
    }


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
                info = await validate_input(self.hass, user_input)
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

        data_schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_OPEN_SWITCH_ENTITY_ID): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "script", "automation", "input_boolean"])
            ),
            vol.Required(CONF_CLOSE_SWITCH_ENTITY_ID): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "script", "automation", "input_boolean"])
            ),
            vol.Optional(CONF_STOP_SWITCH_ENTITY_ID): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "script", "automation", "input_boolean"])
            ),
            vol.Optional(CONF_IS_BUTTON, default=False): bool,
            vol.Required(
                CONF_OPENING_TIME_MAP, 
                default='{"0": 0, "10": 100}'
            ): str,
            vol.Required(
                CONF_CLOSING_TIME_MAP, 
                default='{"0": 100, "10": 0}'
            ): str,
            vol.Optional(CONF_TILTING_TIME_DOWN): vol.All(
                vol.Coerce(float), vol.Range(min=0.1, max=300)
            ),
            vol.Optional(CONF_TILTING_TIME_UP): vol.All(
                vol.Coerce(float), vol.Range(min=0.1, max=300)
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "opening_example": '{"0": 0, "5": 50, "10": 100}',
                "closing_example": '{"0": 100, "8": 20, "10": 0}',
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        config_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except vol.Invalid as err:
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=self._get_reconfigure_schema(config_entry.data),
                    errors={"base": str(err)},
                )
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=self._get_reconfigure_schema(config_entry.data),
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

    def _get_reconfigure_schema(self, data: dict[str, Any]) -> vol.Schema:
        """Get the reconfigure schema with current values."""
        return vol.Schema({
            vol.Required(CONF_NAME, default=data.get(CONF_NAME, "")): str,
            vol.Required(
                CONF_OPEN_SWITCH_ENTITY_ID, 
                default=data.get(CONF_OPEN_SWITCH_ENTITY_ID, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "script", "automation", "input_boolean"])
            ),
            vol.Required(
                CONF_CLOSE_SWITCH_ENTITY_ID, 
                default=data.get(CONF_CLOSE_SWITCH_ENTITY_ID, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "script", "automation", "input_boolean"])
            ),
            vol.Optional(
                CONF_STOP_SWITCH_ENTITY_ID, 
                default=data.get(CONF_STOP_SWITCH_ENTITY_ID, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["switch", "script", "automation", "input_boolean"])
            ),
            vol.Optional(
                CONF_IS_BUTTON, 
                default=data.get(CONF_IS_BUTTON, False)
            ): bool,
            vol.Required(
                CONF_OPENING_TIME_MAP, 
                default=json.dumps(data.get(CONF_OPENING_TIME_MAP, {"0": 0, "10": 100}))
            ): str,
            vol.Required(
                CONF_CLOSING_TIME_MAP, 
                default=json.dumps(data.get(CONF_CLOSING_TIME_MAP, {"0": 100, "10": 0}))
            ): str,
            vol.Optional(
                CONF_TILTING_TIME_DOWN, 
                default=data.get(CONF_TILTING_TIME_DOWN)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=300)),
            vol.Optional(
                CONF_TILTING_TIME_UP, 
                default=data.get(CONF_TILTING_TIME_UP)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=300)),
        })