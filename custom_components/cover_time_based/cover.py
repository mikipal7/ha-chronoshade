"""Cover time based with position-time maps"""

import logging
import re
import time
from asyncio import sleep
from datetime import timedelta
from typing import Dict, Optional, Tuple

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    PLATFORM_SCHEMA,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.const import (
    CONF_NAME,
    ATTR_ENTITY_ID,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_STOP_COVER,
)
from homeassistant.core import callback, HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_platform
from homeassistant.helpers.event import (
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    DOMAIN,
    CONF_OPENING_TIME_MAP,
    CONF_CLOSING_TIME_MAP,
    CONF_TILTING_TIME_DOWN,
    CONF_TILTING_TIME_UP,
    CONF_OPEN_SWITCH_ENTITY_ID,
    CONF_CLOSE_SWITCH_ENTITY_ID,
    CONF_STOP_SWITCH_ENTITY_ID,
    CONF_COVER_ENTITY_ID,
    CONF_IS_BUTTON,
    SERVICE_SET_KNOWN_POSITION,
    SERVICE_SET_KNOWN_TILT_POSITION,
    SERVICE_OPEN_SLACKS,
    SERVICE_CLOSE_SLACKS,
    DEFAULT_TILT_TIME,
)

_LOGGER = logging.getLogger(__name__)

# Legacy platform schema for backward compatibility
CONF_DEVICES = "devices"
CONF_COVER_ENTITY_ID = "cover_entity_id"

BASE_DEVICE_SCHEMA = {
    vol.Required(CONF_NAME): cv.string,
}

TIME_MAP_SCHEMA = vol.Schema({
    vol.Coerce(float): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))
})

SWITCH_COVER_SCHEMA = {
    **BASE_DEVICE_SCHEMA,
    vol.Required(CONF_OPEN_SWITCH_ENTITY_ID): cv.entity_id,
    vol.Required(CONF_CLOSE_SWITCH_ENTITY_ID): cv.entity_id,
    vol.Optional(CONF_STOP_SWITCH_ENTITY_ID, default=None): vol.Any(cv.entity_id, None),
    vol.Optional(CONF_IS_BUTTON, default=False): cv.boolean,
    vol.Required(CONF_OPENING_TIME_MAP): TIME_MAP_SCHEMA,
    vol.Required(CONF_CLOSING_TIME_MAP): TIME_MAP_SCHEMA,
    vol.Optional(CONF_TILTING_TIME_DOWN, default=None): vol.Any(cv.positive_float, None),
    vol.Optional(CONF_TILTING_TIME_UP, default=None): vol.Any(cv.positive_float, None),
}

ENTITY_COVER_SCHEMA = {
    **BASE_DEVICE_SCHEMA,
    vol.Required(CONF_COVER_ENTITY_ID): cv.entity_id,
    vol.Required(CONF_OPENING_TIME_MAP): TIME_MAP_SCHEMA,
    vol.Required(CONF_CLOSING_TIME_MAP): TIME_MAP_SCHEMA,
    vol.Optional(CONF_TILTING_TIME_DOWN, default=None): vol.Any(cv.positive_float, None),
    vol.Optional(CONF_TILTING_TIME_UP, default=None): vol.Any(cv.positive_float, None),
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_DEVICES, default={}): vol.Schema(
            {cv.string: vol.Schema(vol.Any(SWITCH_COVER_SCHEMA, ENTITY_COVER_SCHEMA))}
        ),
    }
)

POSITION_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_POSITION): cv.positive_int,
    }
)
TILT_POSITION_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_TILT_POSITION): cv.positive_int,
    }
)

DOMAIN = "cover_time_based"


class PositionCalculator:
    """Calculate cover position based on time maps."""
    
    def __init__(self, opening_time_map: Dict[float, int], closing_time_map: Dict[float, int]):
        """Initialize the position calculator."""
        self._opening_time_map = self._validate_and_sort_time_map(opening_time_map, "opening")
        self._closing_time_map = self._validate_and_sort_time_map(closing_time_map, "closing")
        
        self._current_position = 0  # 0 = closed, 100 = open
        self._is_moving = False
        self._movement_start_time = None
        self._movement_direction = None  # "opening" or "closing"
        self._target_position = None
        self._start_position = None  # Position when movement started
        self._movement_duration = None  # How long the movement should take
    
    def _validate_and_sort_time_map(self, time_map: Dict[float, int], map_type: str) -> Dict[float, int]:
        """Validate and sort time map."""
        if not time_map:
            raise vol.Invalid(f"{map_type} time map cannot be empty")
        
        # Sort by time
        sorted_map = dict(sorted(time_map.items()))
        times = list(sorted_map.keys())
        positions = list(sorted_map.values())
        
        # Validate time progression
        if times[0] != 0:
            raise vol.Invalid(f"{map_type} time map must start at time 0")
        
        # Validate position range
        for pos in positions:
            if not 0 <= pos <= 100:
                raise vol.Invalid(f"Position {pos} in {map_type} time map must be between 0 and 100")
        
        # Validate start/end positions
        if map_type == "opening":
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
        if map_type == "opening":
            for i in range(1, len(positions)):
                if positions[i] < positions[i-1]:
                    raise vol.Invalid("Opening time map positions must be non-decreasing")
        else:  # closing
            for i in range(1, len(positions)):
                if positions[i] > positions[i-1]:
                    raise vol.Invalid("Closing time map positions must be non-increasing")
        
        return sorted_map
    
    def _interpolate_position(self, elapsed_time: float, time_map: Dict[float, int]) -> int:
        """Interpolate position based on elapsed time and time map."""
        times = list(time_map.keys())
        positions = list(time_map.values())
        
        # If elapsed time is before first time point
        if elapsed_time <= times[0]:
            return positions[0]
        
        # If elapsed time is after last time point
        if elapsed_time >= times[-1]:
            return positions[-1]
        
        # Find the two time points to interpolate between
        for i in range(len(times) - 1):
            if times[i] <= elapsed_time <= times[i + 1]:
                # Linear interpolation
                time_diff = times[i + 1] - times[i]
                pos_diff = positions[i + 1] - positions[i]
                time_ratio = (elapsed_time - times[i]) / time_diff
                interpolated_pos = positions[i] + (pos_diff * time_ratio)
                return round(interpolated_pos)
        
        return positions[-1]
    
    def _find_time_for_position(self, target_position: int, time_map: Dict[float, int]) -> float:
        """Find the time needed to reach a target position."""
        times = list(time_map.keys())
        positions = list(time_map.values())
        
        # If target is at a defined position
        if target_position in positions:
            idx = positions.index(target_position)
            return times[idx]
        
        # Find the two positions to interpolate between
        for i in range(len(positions) - 1):
            pos1, pos2 = positions[i], positions[i + 1]
            if min(pos1, pos2) <= target_position <= max(pos1, pos2):
                # Linear interpolation to find time
                time1, time2 = times[i], times[i + 1]
                pos_diff = pos2 - pos1
                if pos_diff == 0:  # Same position
                    return time1
                time_diff = time2 - time1
                pos_ratio = (target_position - pos1) / pos_diff
                interpolated_time = time1 + (time_diff * pos_ratio)
                return interpolated_time
        
        # Target position not reachable
        return times[-1]
    
    def _calculate_movement_duration(self, start_pos: int, target_pos: int, direction: str) -> float:
        """Calculate how long the movement should take based on the time map."""
        if direction == "opening":
            time_map = self._opening_time_map
        else:
            time_map = self._closing_time_map
        
        start_time = self._find_time_for_position(start_pos, time_map)
        target_time = self._find_time_for_position(target_pos, time_map)
        
        return abs(target_time - start_time)
    
    def start_opening(self, target_position: int = 100):
        """Start opening movement to target position."""
        if target_position <= self._current_position:
            return  # Already at or past target
        
        self._is_moving = True
        self._movement_direction = "opening"
        self._movement_start_time = time.time()
        self._start_position = self._current_position
        self._target_position = target_position
        self._movement_duration = self._calculate_movement_duration(
            self._current_position, target_position, "opening"
        )
        
        _LOGGER.debug(f"Starting opening from {self._current_position} to {target_position}, duration: {self._movement_duration}s")
    
    def start_closing(self, target_position: int = 0):
        """Start closing movement to target position."""
        if target_position >= self._current_position:
            return  # Already at or past target
        
        self._is_moving = True
        self._movement_direction = "closing"
        self._movement_start_time = time.time()
        self._start_position = self._current_position
        self._target_position = target_position
        self._movement_duration = self._calculate_movement_duration(
            self._current_position, target_position, "closing"
        )
        
        _LOGGER.debug(f"Starting closing from {self._current_position} to {target_position}, duration: {self._movement_duration}s")
    
    def get_current_position(self) -> int:
        """Get current position, updating if moving."""
        if not self._is_moving:
            return self._current_position
        
        elapsed_time = time.time() - self._movement_start_time
        
        # Calculate progress as a ratio (0.0 to 1.0)
        if self._movement_duration > 0:
            progress = min(elapsed_time / self._movement_duration, 1.0)
        else:
            progress = 1.0
        
        # Linear interpolation between start and target position
        position_diff = self._target_position - self._start_position
        new_position = self._start_position + (position_diff * progress)
        
        self._current_position = round(new_position)
        return self._current_position
    
    def is_moving(self) -> bool:
        """Check if cover is currently moving."""
        return self._is_moving
    
    def has_reached_target(self) -> bool:
        """Check if cover has reached its target position."""
        if not self._is_moving:
            return True
        
        current_pos = self.get_current_position()
        
        # Check if we've reached the target position or time
        elapsed_time = time.time() - self._movement_start_time
        time_reached = elapsed_time >= self._movement_duration
        
        if self._movement_direction == "opening":
            position_reached = current_pos >= self._target_position
        else:  # closing
            position_reached = current_pos <= self._target_position
        
        return time_reached or position_reached
    
    def stop(self):
        """Stop movement and update current position."""
        if self._is_moving:
            self._current_position = self.get_current_position()
            self._is_moving = False
            self._movement_start_time = None
            self._movement_direction = None
            self._target_position = None
            self._start_position = None
            self._movement_duration = None
            _LOGGER.debug(f"Stopped at position {self._current_position}")
    
    def set_position(self, position: int):
        """Set known position."""
        self.stop()
        self._current_position = max(0, min(100, position))
        _LOGGER.debug(f"Set known position to {self._current_position}")
    
    def is_closed(self) -> bool:
        """Check if cover is closed."""
        return self.get_current_position() == 0
    
    def is_open(self) -> bool:
        """Check if cover is open."""
        return self.get_current_position() == 100

class TiltCalculator:
    """Simple linear tilt calculator (unchanged from original logic)."""
    
    def __init__(self, tilt_time_down: float, tilt_time_up: float):
        """Initialize tilt calculator."""
        self._tilt_time_down = tilt_time_down
        self._tilt_time_up = tilt_time_up
        self._current_position = 0  # 0 = closed, 100 = open
        self._is_moving = False
        self._movement_start_time = None
        self._movement_direction = None
        self._target_position = None
    
    def start_opening(self, target_position: int = 100):
        """Start opening tilt."""
        if target_position <= self._current_position:
            return
        
        self._is_moving = True
        self._movement_direction = "opening"
        self._movement_start_time = time.time()
        self._target_position = target_position
    
    def start_closing(self, target_position: int = 0):
        """Start closing tilt."""
        if target_position >= self._current_position:
            return
        
        self._is_moving = True
        self._movement_direction = "closing"
        self._movement_start_time = time.time()
        self._target_position = target_position
    
    def get_current_position(self) -> int:
        """Get current tilt position."""
        if not self._is_moving:
            return self._current_position
        
        elapsed_time = time.time() - self._movement_start_time
        
        if self._movement_direction == "opening":
            total_time = self._tilt_time_up
            progress = min(elapsed_time / total_time, 1.0)
            new_position = self._current_position + (self._target_position - self._current_position) * progress
        else:  # closing
            total_time = self._tilt_time_down
            progress = min(elapsed_time / total_time, 1.0)
            new_position = self._current_position + (self._target_position - self._current_position) * progress
        
        self._current_position = round(new_position)
        return self._current_position
    
    def is_moving(self) -> bool:
        """Check if tilt is moving."""
        return self._is_moving
    
    def has_reached_target(self) -> bool:
        """Check if tilt has reached target."""
        if not self._is_moving:
            return True
        
        current_pos = self.get_current_position()
        return current_pos == self._target_position
    
    def stop(self):
        """Stop tilt movement."""
        if self._is_moving:
            self._current_position = self.get_current_position()
            self._is_moving = False
            self._movement_start_time = None
            self._movement_direction = None
            self._target_position = None
    
    def set_position(self, position: int):
        """Set known tilt position."""
        self.stop()
        self._current_position = max(0, min(100, position))


def devices_from_config(domain_config):
    """Parse configuration and add cover devices."""
    devices = []
    for device_id, config in domain_config[CONF_DEVICES].items():
        name = config.pop(CONF_NAME)
        
        opening_time_map = config.pop(CONF_OPENING_TIME_MAP)
        closing_time_map = config.pop(CONF_CLOSING_TIME_MAP)
        tilt_time_down = config.pop(CONF_TILTING_TIME_DOWN)
        tilt_time_up = config.pop(CONF_TILTING_TIME_UP)
        
        open_switch_entity_id = config.pop(CONF_OPEN_SWITCH_ENTITY_ID, None)
        close_switch_entity_id = config.pop(CONF_CLOSE_SWITCH_ENTITY_ID, None)
        stop_switch_entity_id = config.pop(CONF_STOP_SWITCH_ENTITY_ID, None)
        is_button = config.pop(CONF_IS_BUTTON, False)
        cover_entity_id = config.pop(CONF_COVER_ENTITY_ID, None)
        
        device = CoverTimeBased(
            device_id,
            name,
            opening_time_map,
            closing_time_map,
            tilt_time_down,
            tilt_time_up,
            open_switch_entity_id,
            close_switch_entity_id,
            stop_switch_entity_id,
            is_button,
            cover_entity_id,
        )
        devices.append(device)
    return devices


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cover Time Based from a config entry."""
    config = config_entry.data
    
    # Create cover entity from config entry
    cover = CoverTimeBased(
        device_id=config_entry.entry_id,
        name=config[CONF_NAME],
        opening_time_map=config[CONF_OPENING_TIME_MAP],
        closing_time_map=config[CONF_CLOSING_TIME_MAP],
        tilt_time_down=config.get(CONF_TILTING_TIME_DOWN),
        tilt_time_up=config.get(CONF_TILTING_TIME_UP),
        open_switch_entity_id=config.get(CONF_OPEN_SWITCH_ENTITY_ID),
        close_switch_entity_id=config.get(CONF_CLOSE_SWITCH_ENTITY_ID),
        stop_switch_entity_id=config.get(CONF_STOP_SWITCH_ENTITY_ID),
        is_button=config.get(CONF_IS_BUTTON, False),
        cover_entity_id=config.get(CONF_COVER_ENTITY_ID),
    )
    
    async_add_entities([cover])
    
    # Register services
    platform = entity_platform.current_platform.get()
    if platform:
        platform.async_register_entity_service(
            SERVICE_SET_KNOWN_POSITION, POSITION_SCHEMA, "set_known_position"
        )
        platform.async_register_entity_service(
            SERVICE_SET_KNOWN_TILT_POSITION, TILT_POSITION_SCHEMA, "set_known_tilt_position"
        )
        platform.async_register_entity_service(
            SERVICE_OPEN_SLACKS, {}, "async_open_slacks"
        )
        platform.async_register_entity_service(
            SERVICE_CLOSE_SLACKS, {}, "async_close_slacks"
        )


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the cover platform (legacy YAML support)."""
    async_add_entities(devices_from_config(config))
    
    platform = entity_platform.current_platform.get()
    
    platform.async_register_entity_service(
        SERVICE_SET_KNOWN_POSITION, POSITION_SCHEMA, "set_known_position"
    )
    platform.async_register_entity_service(
        SERVICE_SET_KNOWN_TILT_POSITION, TILT_POSITION_SCHEMA, "set_known_tilt_position"
    )
    platform.async_register_entity_service(
        SERVICE_OPEN_SLACKS, {}, "async_open_slacks"
    )
    platform.async_register_entity_service(
        SERVICE_CLOSE_SLACKS, {}, "async_close_slacks"
    )


class CoverTimeBased(CoverEntity, RestoreEntity):
    """Cover entity with time-based position maps."""
    
    def __init__(
        self,
        device_id,
        name,
        opening_time_map,
        closing_time_map,
        tilt_time_down,
        tilt_time_up,
        open_switch_entity_id,
        close_switch_entity_id,
        stop_switch_entity_id,
        is_button,
        cover_entity_id,
    ):
        """Initialize the cover."""
        # Use name-based unique_id for stability across HA updates
        self._unique_id = re.sub(r'[^a-z0-9_]', '_', name.lower())
        self._device_id = device_id
        self._name = name or device_id
        
        # Initialize position calculator
        self.position_calc = PositionCalculator(opening_time_map, closing_time_map)
        
        # Initialize tilt calculator if supported
        self._tilt_time_down = tilt_time_down
        self._tilt_time_up = tilt_time_up
        if self._has_tilt_support():
            self.tilt_calc = TiltCalculator(tilt_time_down, tilt_time_up)
        
        # Switch/entity configuration
        self._open_switch_entity_id = open_switch_entity_id
        self._close_switch_entity_id = close_switch_entity_id
        self._stop_switch_entity_id = stop_switch_entity_id
        self._is_button = is_button
        self._cover_entity_id = cover_entity_id
        
        self._unsubscribe_auto_updater = None
    
    async def async_added_to_hass(self):
        """Restore previous state."""
        old_state = await self.async_get_last_state()
        _LOGGER.debug("async_added_to_hass :: oldState %s", old_state)
        
        if old_state is not None and old_state.attributes.get(ATTR_CURRENT_POSITION) is not None:
            position = int(old_state.attributes.get(ATTR_CURRENT_POSITION))
            self.position_calc.set_position(position)
            
            if (self._has_tilt_support() and 
                old_state.attributes.get(ATTR_CURRENT_TILT_POSITION) is not None):
                tilt_position = int(old_state.attributes.get(ATTR_CURRENT_TILT_POSITION))
                self.tilt_calc.set_position(tilt_position)
    
    @property
    def name(self):
        """Return the name of the cover."""
        return self._name
    
    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{DOMAIN}_{self._unique_id}"
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._name,
            manufacturer="Cover Time Based",
            model="Time-based Cover Controller",
            sw_version="4.0.0",
        )
    
    @property
    def device_class(self):
        """Return the device class of the cover."""
        return None
    
    @property
    def extra_state_attributes(self):
        """Return the device state attributes."""
        return {}
    
    @property
    def current_cover_position(self) -> int | None:
        """Return the current position of the cover."""
        return self.position_calc.get_current_position()
    
    @property
    def current_cover_tilt_position(self) -> int | None:
        """Return the current tilt of the cover."""
        if self._has_tilt_support():
            return self.tilt_calc.get_current_position()
        return None
    
    @property
    def is_opening(self):
        """Return if the cover is opening or not."""
        return (self.position_calc.is_moving() and 
                self.position_calc._movement_direction == "opening") or \
               (self._has_tilt_support() and self.tilt_calc.is_moving() and 
                self.tilt_calc._movement_direction == "opening")
    
    @property
    def is_closing(self):
        """Return if the cover is closing or not."""
        return (self.position_calc.is_moving() and 
                self.position_calc._movement_direction == "closing") or \
               (self._has_tilt_support() and self.tilt_calc.is_moving() and 
                self.tilt_calc._movement_direction == "closing")
    
    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self.position_calc.is_closed()
    
    @property
    def assumed_state(self):
        """Return True because covers can be stopped midway."""
        return True
    
    @property
    def supported_features(self) -> CoverEntityFeature:
        """Flag supported features."""
        supported_features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | 
            CoverEntityFeature.STOP | CoverEntityFeature.SET_POSITION
        )
        
        if self._has_tilt_support():
            supported_features |= (
                CoverEntityFeature.OPEN_TILT | CoverEntityFeature.CLOSE_TILT | 
                CoverEntityFeature.STOP_TILT | CoverEntityFeature.SET_TILT_POSITION
            )
        
        return supported_features
    
    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        if ATTR_POSITION in kwargs:
            position = kwargs[ATTR_POSITION]
            _LOGGER.debug("async_set_cover_position: %d", position)
            await self.set_position(position)
    
    async def async_set_cover_tilt_position(self, **kwargs):
        """Move the cover tilt to a specific position."""
        if ATTR_TILT_POSITION in kwargs:
            position = kwargs[ATTR_TILT_POSITION]
            _LOGGER.debug("async_set_cover_tilt_position: %d", position)
            await self.set_tilt_position(position)
    
    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        _LOGGER.debug("async_close_cover")
        current_position = self.position_calc.get_current_position()
        if current_position > 0:
            self.position_calc.start_closing()
            self.start_auto_updater()
            self._update_tilt_before_travel(SERVICE_CLOSE_COVER)
            await self._async_handle_command(SERVICE_CLOSE_COVER)
    
    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        _LOGGER.debug("async_open_cover")
        current_position = self.position_calc.get_current_position()
        if current_position < 100:
            self.position_calc.start_opening()
            self.start_auto_updater()
            self._update_tilt_before_travel(SERVICE_OPEN_COVER)
            await self._async_handle_command(SERVICE_OPEN_COVER)
    
    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        _LOGGER.debug("async_close_cover_tilt")
        if self._has_tilt_support():
            current_position = self.tilt_calc.get_current_position()
            if current_position > 0:
                self.tilt_calc.start_closing()
                self.start_auto_updater()
                await self._async_handle_command(SERVICE_CLOSE_COVER)
    
    async def async_open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        _LOGGER.debug("async_open_cover_tilt")
        if self._has_tilt_support():
            current_position = self.tilt_calc.get_current_position()
            if current_position < 100:
                self.tilt_calc.start_opening()
                self.start_auto_updater()
                await self._async_handle_command(SERVICE_OPEN_COVER)
    
    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        _LOGGER.debug("async_stop_cover")
        self._handle_stop()
        await self._async_handle_command(SERVICE_STOP_COVER)
    
    async def async_open_slacks(self, **kwargs):
        """Open the slacks of the cover (not applicable with time maps)."""
        _LOGGER.debug("async_open_slacks - not implemented for time map based covers")
    
    async def async_close_slacks(self, **kwargs):
        """Close the slacks of the cover (not applicable with time maps)."""
        _LOGGER.debug("async_close_slacks - not implemented for time map based covers")
    
    async def set_position(self, position):
        """Move cover to a designated position."""
        _LOGGER.debug("set_position to %d", position)
        current_position = self.position_calc.get_current_position()
        
        if position > current_position:
            # Need to open
            self.position_calc.start_opening(position)
            self.start_auto_updater()
            self._update_tilt_before_travel(SERVICE_OPEN_COVER)
            await self._async_handle_command(SERVICE_OPEN_COVER)
        elif position < current_position:
            # Need to close
            self.position_calc.start_closing(position)
            self.start_auto_updater()
            self._update_tilt_before_travel(SERVICE_CLOSE_COVER)
            await self._async_handle_command(SERVICE_CLOSE_COVER)
    
    async def set_tilt_position(self, position):
        """Move cover tilt to a designated position."""
        if not self._has_tilt_support():
            return
        
        _LOGGER.debug("set_tilt_position to %d", position)
        current_position = self.tilt_calc.get_current_position()
        
        if position > current_position:
            self.tilt_calc.start_opening(position)
            self.start_auto_updater()
            await self._async_handle_command(SERVICE_OPEN_COVER)
        elif position < current_position:
            self.tilt_calc.start_closing(position)
            self.start_auto_updater()
            await self._async_handle_command(SERVICE_CLOSE_COVER)
    
    def _handle_stop(self):
        """Handle stop command."""
        if self.position_calc.is_moving():
            _LOGGER.debug("_handle_stop :: stopping cover movement")
            self.position_calc.stop()
            self.stop_auto_updater()
        
        if self._has_tilt_support() and self.tilt_calc.is_moving():
            _LOGGER.debug("_handle_stop :: stopping tilt movement")
            self.tilt_calc.stop()
            self.stop_auto_updater()
    
    def start_auto_updater(self):
        """Start the autoupdater to update HASS while cover is moving."""
        _LOGGER.debug("start_auto_updater")
        if self._unsubscribe_auto_updater is None:
            _LOGGER.debug("init _unsubscribe_auto_updater")
            interval = timedelta(seconds=0.1)
            self._unsubscribe_auto_updater = async_track_time_interval(
                self.hass, self.auto_updater_hook, interval
            )
    
    @callback
    def auto_updater_hook(self, now):
        """Call for the autoupdater."""
        _LOGGER.debug("auto_updater_hook")
        self.async_schedule_update_ha_state()
        if self.position_reached():
            _LOGGER.debug("auto_updater_hook :: position_reached")
            self.stop_auto_updater()
        self.hass.async_create_task(self.auto_stop_if_necessary())
    
    def stop_auto_updater(self):
        """Stop the autoupdater."""
        _LOGGER.debug("stop_auto_updater")
        if self._unsubscribe_auto_updater is not None:
            self._unsubscribe_auto_updater()
            self._unsubscribe_auto_updater = None
    
    def position_reached(self):
        """Return if cover has reached its final position."""
        return self.position_calc.has_reached_target() and (
            not self._has_tilt_support() or self.tilt_calc.has_reached_target()
        )
    
    def _has_tilt_support(self):
        """Return if cover has tilt support."""
        return self._tilt_time_down is not None and self._tilt_time_up is not None
    
    def _update_tilt_before_travel(self, command):
        """Updating tilt before travel."""
        if self._has_tilt_support():
            _LOGGER.debug("_update_tilt_before_travel :: command %s", command)
            if command == SERVICE_OPEN_COVER:
                self.tilt_calc.set_position(0)
            elif command == SERVICE_CLOSE_COVER:
                self.tilt_calc.set_position(100)
    
    async def auto_stop_if_necessary(self):
        """Do auto stop if necessary."""
        if self.position_reached():
            _LOGGER.debug("auto_stop_if_necessary :: calling stop command")
            self.position_calc.stop()
            if self._has_tilt_support():
                self.tilt_calc.stop()
            await self._async_handle_command(SERVICE_STOP_COVER)
    
    async def set_known_position(self, **kwargs):
        """Set a known position for the cover."""
        position = kwargs[ATTR_POSITION]
        self._handle_stop()
        await self._async_handle_command(SERVICE_STOP_COVER)
        self.position_calc.set_position(position)
    
    async def set_known_tilt_position(self, **kwargs):
        """Set a known tilt position for the cover."""
        if not self._has_tilt_support():
            return
        position = kwargs[ATTR_TILT_POSITION]
        await self._async_handle_command(SERVICE_STOP_COVER)
        self.tilt_calc.set_position(position)
    
    async def _async_handle_command(self, command, *args):
        """Handle cover commands."""
        if command == SERVICE_CLOSE_COVER:
            cmd = "DOWN"
            self._state = False
            if self._cover_entity_id is not None:
                await self.hass.services.async_call(
                    "cover",
                    "close_cover",
                    {"entity_id": self._cover_entity_id},
                    False,
                )
            else:
                # Turn off open entity first
                await self._async_call_entity_service(self._open_switch_entity_id, "turn_off")
                
                # Turn on close entity
                await self._async_call_entity_service(self._close_switch_entity_id, "turn_on")
                
                # Turn off stop entity if exists
                if self._stop_switch_entity_id is not None:
                    await self._async_call_entity_service(self._stop_switch_entity_id, "turn_off")

                if self._is_button:
                    # The close_switch_entity_id should be turned off one second after being turned on
                    await sleep(1)
                    await self._async_call_entity_service(self._close_switch_entity_id, "turn_off")

        elif command == SERVICE_OPEN_COVER:
            cmd = "UP"
            self._state = True
            if self._cover_entity_id is not None:
                await self.hass.services.async_call(
                    "cover",
                    "open_cover",
                    {"entity_id": self._cover_entity_id},
                    False,
                )
            else:
                # Turn off close entity first
                await self._async_call_entity_service(self._close_switch_entity_id, "turn_off")
                
                # Turn on open entity
                await self._async_call_entity_service(self._open_switch_entity_id, "turn_on")
                
                # Turn off stop entity if exists
                if self._stop_switch_entity_id is not None:
                    await self._async_call_entity_service(self._stop_switch_entity_id, "turn_off")
                
                if self._is_button:
                    # The open_switch_entity_id should be turned off one second after being turned on
                    await sleep(1)
                    await self._async_call_entity_service(self._open_switch_entity_id, "turn_off")

        elif command == SERVICE_STOP_COVER:
            cmd = "STOP"
            self._state = True
            if self._cover_entity_id is not None:
                await self.hass.services.async_call(
                    "cover",
                    "stop_cover",
                    {"entity_id": self._cover_entity_id},
                    False,
                )
            else:
                # Turn off close and open entities
                await self._async_call_entity_service(self._close_switch_entity_id, "turn_off")
                await self._async_call_entity_service(self._open_switch_entity_id, "turn_off")
                
                # Turn on stop entity if exists
                if self._stop_switch_entity_id is not None:
                    await self._async_call_entity_service(self._stop_switch_entity_id, "turn_on")

                    if self._is_button:
                        # The stop_switch_entity_id should be turned off one second after being turned on
                        await sleep(1)
                        await self._async_call_entity_service(self._stop_switch_entity_id, "turn_off")

        _LOGGER.debug("_async_handle_command :: %s", cmd)

        # Update state of entity
        self.async_write_ha_state()
    
    async def _async_call_entity_service(self, entity_id: str, action: str):
        """Call appropriate service based on entity type."""
        if not entity_id:
            return
        
        domain = entity_id.split('.')[0]
        
        if domain == "script":
            if action == "turn_on":
                await self.hass.services.async_call("script", "turn_on", {"entity_id": entity_id}, False)
            # Scripts don't have turn_off, so we ignore turn_off calls
        elif domain == "automation":
            if action == "turn_on":
                await self.hass.services.async_call("automation", "trigger", {"entity_id": entity_id}, False)
            # Automations don't have turn_off in this context, so we ignore turn_off calls
        else:
            # For switches, input_boolean, and other entities that support turn_on/turn_off
            await self.hass.services.async_call("homeassistant", action, {"entity_id": entity_id}, False)
