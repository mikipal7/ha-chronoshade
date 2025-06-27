"""Cover time based with improved non-linear movement support"""

import logging
from asyncio import sleep
from datetime import timedelta
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
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
from homeassistant.core import callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

_LOGGER = logging.getLogger(__name__)

CONF_DEVICES = "devices"
CONF_TRAVEL_TIME = "travel_time"
CONF_OPEN_MAP = "open_map"
CONF_CLOSE_MAP = "close_map"
CONF_TILT_OPEN_MAP = "tilt_open_map"
CONF_TILT_CLOSE_MAP = "tilt_close_map"
DEFAULT_TRAVEL_TIME = 30

CONF_OPEN_SWITCH_ENTITY_ID = "open_switch_entity_id"
CONF_CLOSE_SWITCH_ENTITY_ID = "close_switch_entity_id"
CONF_STOP_SWITCH_ENTITY_ID = "stop_switch_entity_id"
CONF_IS_BUTTON = "is_button"
CONF_COVER_ENTITY_ID = "cover_entity_id"

SERVICE_SET_KNOWN_POSITION = "set_known_position"
SERVICE_SET_KNOWN_TILT_POSITION = "set_known_tilt_position"

BASE_DEVICE_SCHEMA = {
    vol.Required(CONF_NAME): cv.string,
}

POSITION_MAP_SCHEMA = vol.All(
    dict,
    vol.Schema({
        vol.All(vol.Coerce(float), vol.Range(min=0)): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))
    })
)

TRAVEL_SCHEMA = {
    vol.Optional(CONF_TRAVEL_TIME, default=DEFAULT_TRAVEL_TIME): cv.positive_int,
    vol.Optional(CONF_OPEN_MAP): POSITION_MAP_SCHEMA,
    vol.Optional(CONF_CLOSE_MAP): POSITION_MAP_SCHEMA,
}

TILT_SCHEMA = {
    vol.Optional(CONF_TILT_OPEN_MAP): POSITION_MAP_SCHEMA,
    vol.Optional(CONF_TILT_CLOSE_MAP): POSITION_MAP_SCHEMA,
}

SWITCH_COVER_SCHEMA = {
    **BASE_DEVICE_SCHEMA,
    vol.Required(CONF_OPEN_SWITCH_ENTITY_ID): cv.entity_id,
    vol.Required(CONF_CLOSE_SWITCH_ENTITY_ID): cv.entity_id,
    vol.Optional(CONF_STOP_SWITCH_ENTITY_ID): cv.entity_id,
    vol.Optional(CONF_IS_BUTTON, default=False): cv.boolean,
    **TRAVEL_SCHEMA,
    **TILT_SCHEMA,
}

ENTITY_COVER_SCHEMA = {
    **BASE_DEVICE_SCHEMA,
    vol.Required(CONF_COVER_ENTITY_ID): cv.entity_id,
    **TRAVEL_SCHEMA,
    **TILT_SCHEMA,
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_DEVICES, default={}): vol.Schema({
        cv.string: vol.Any(SWITCH_COVER_SCHEMA, ENTITY_COVER_SCHEMA)
    }),
})

class PositionCalculator:
    """Calculate position based on time using position maps."""
    
    def __init__(self, open_map=None, close_map=None, travel_time=None):
        """Initialize with movement maps."""
        self.open_map = self._normalize_map(open_map) if open_map else None
        self.close_map = self._normalize_map(close_map) if close_map else None
        self.travel_time = travel_time
        self._start_time = None
        self._start_position = None
        self._target_position = None
        self._current_position = None
        self._direction = None

    def _normalize_map(self, pos_map):
        """Convert dict to sorted list of time-position pairs."""
        return sorted((float(t), p) for t, p in pos_map.items())

    def start_travel(self, target_position, current_position=None):
        """Start traveling to target position."""
        self._start_time = None
        self._target_position = target_position
        self._current_position = current_position if current_position is not None else self._current_position
        self._start_position = self._current_position or (0 if target_position > 0 else 100)
        self._direction = "open" if target_position < self._start_position else "close"

    def update_position(self, now):
        """Update position based on current time."""
        if self._start_time is None:
            self._start_time = now
            return self._start_position
        
        if not self.is_traveling():
            return self._current_position
        
        elapsed = (now - self._start_time).total_seconds()
        movement_map = self.open_map if self._direction == "open" else self.close_map

        if movement_map:
            # Find the two points in the map that bracket the elapsed time
            prev_time, prev_pos = movement_map[0]
            next_time, next_pos = movement_map[-1]
            
            for time, pos in movement_map[1:]:
                if time <= elapsed:
                    prev_time, prev_pos = time, pos
                else:
                    next_time, next_pos = time, pos
                    break
            
            if elapsed >= next_time:
                self._current_position = self._target_position
                return self._current_position
                
            # Linear interpolation between points
            time_diff = next_time - prev_time
            ratio = (elapsed - prev_time) / time_diff if time_diff else 0
            pos_diff = next_pos - prev_pos
            self._current_position = prev_pos + (pos_diff * ratio)
        else:
            # Linear movement based on travel time
            progress = min(1.0, elapsed / self.travel_time)
            pos_diff = self._target_position - self._start_position
            self._current_position = self._start_position + (pos_diff * progress)
        
        # Check if we've reached the target
        if ((self._direction == "open" and self._current_position <= self._target_position) or
            (self._direction == "close" and self._current_position >= self._target_position)):
            self._current_position = self._target_position
        
        return self._current_position

    def stop(self):
        """Stop traveling."""
        self._target_position = self._current_position

    def is_traveling(self):
        """Return if traveling."""
        return (self._current_position is not None and 
                self._target_position is not None and
                abs(self._current_position - self._target_position) > 0.5)

    def current_position(self):
        """Return current position."""
        return self._current_position

    def position_reached(self):
        """Return if position is reached."""
        return not self.is_traveling()

    def is_closed(self):
        """Return if cover is closed."""
        return self._current_position == 100

    def is_open(self):
        """Return if cover is open."""
        return self._current_position == 0

    def set_position(self, position):
        """Set position directly."""
        self._current_position = position
        self._target_position = position

class CoverTimeBased(CoverEntity, RestoreEntity):
    """Representation of a time based cover."""

    def __init__(
        self,
        device_id,
        name,
        open_switch_entity_id=None,
        close_switch_entity_id=None,
        stop_switch_entity_id=None,
        is_button=False,
        cover_entity_id=None,
        travel_time=DEFAULT_TRAVEL_TIME,
        open_map=None,
        close_map=None,
        tilt_open_map=None,
        tilt_close_map=None,
    ):
        """Initialize the cover."""
        self._unique_id = device_id
        self._name = name or device_id
        self._open_switch_entity_id = open_switch_entity_id
        self._close_switch_entity_id = close_switch_entity_id
        self._stop_switch_entity_id = stop_switch_entity_id
        self._is_button = is_button
        self._cover_entity_id = cover_entity_id
        self._unsubscribe_auto_updater = None

        # Initialize position calculators
        self.position_calc = PositionCalculator(open_map, close_map, travel_time)
        self.tilt_calc = PositionCalculator(tilt_open_map, tilt_close_map) if (tilt_open_map or tilt_close_map) else None

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"cover_timebased_{self._unique_id}"

    @property
    def current_cover_position(self):
        """Return current position of cover."""
        pos = self.position_calc.current_position()
        return 100 - pos if pos is not None else None

    @property
    def current_cover_tilt_position(self):
        """Return current tilt position."""
        if not self._has_tilt_support:
            return None
        pos = self.tilt_calc.current_position()
        return 100 - pos if pos is not None else None

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self.position_calc.is_closed()

    @property
    def is_opening(self):
        """Return if the cover is opening."""
        return (self.position_calc.is_traveling() and 
                self.position_calc._direction == "open")

    @property
    def is_closing(self):
        """Return if the cover is closing."""
        return (self.position_calc.is_traveling() and 
                self.position_calc._direction == "close")

    @property
    def _has_tilt_support(self):
        """Return if cover has tilt support."""
        return self.tilt_calc is not None

    @property
    def supported_features(self):
        """Flag supported features."""
        features = (CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | 
                   CoverEntityFeature.STOP | CoverEntityFeature.SET_POSITION)
        
        if self._has_tilt_support:
            features |= (CoverEntityFeature.OPEN_TILT | CoverEntityFeature.CLOSE_TILT |
                        CoverEntityFeature.STOP_TILT | CoverEntityFeature.SET_TILT_POSITION)
        
        return features

    async def async_added_to_hass(self):
        """Restore state on startup."""
        await super().async_added_to_hass()
        if (state := await self.async_get_last_state()) and state.attributes.get(ATTR_CURRENT_POSITION):
            self.position_calc.set_position(100 - state.attributes[ATTR_CURRENT_POSITION])
            if self._has_tilt_support and state.attributes.get(ATTR_CURRENT_TILT_POSITION):
                self.tilt_calc.set_position(100 - state.attributes[ATTR_CURRENT_TILT_POSITION])

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        if self.position_calc.current_position() != 0:
            self.position_calc.start_travel(0)
            self.start_auto_updater()
            await self._async_handle_command(SERVICE_OPEN_COVER)

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        if self.position_calc.current_position() != 100:
            self.position_calc.start_travel(100)
            self.start_auto_updater()
            await self._async_handle_command(SERVICE_CLOSE_COVER)

    async def async_set_cover_position(self, **kwargs):
        """Move cover to a specific position."""
        position = kwargs[ATTR_POSITION]
        target = 100 - position
        self.position_calc.start_travel(target)
        self.start_auto_updater()
        command = SERVICE_OPEN_COVER if target < (self.position_calc.current_position() or 100) else SERVICE_CLOSE_COVER
        await self._async_handle_command(command)

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self.position_calc.stop()
        if self._has_tilt_support:
            self.tilt_calc.stop()
        self.stop_auto_updater()
        await self._async_handle_command(SERVICE_STOP_COVER)

    # Tilt methods (only if tilt support exists)
    async def async_open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        if self._has_tilt_support and self.tilt_calc.current_position() != 0:
            self.tilt_calc.start_travel(0)
            self.start_auto_updater()
            await self._async_handle_command(SERVICE_OPEN_COVER)

    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        if self._has_tilt_support and self.tilt_calc.current_position() != 100:
            self.tilt_calc.start_travel(100)
            self.start_auto_updater()
            await self._async_handle_command(SERVICE_CLOSE_COVER)

    async def async_set_cover_tilt_position(self, **kwargs):
        """Move cover tilt to a specific position."""
        if not self._has_tilt_support:
            return
        position = kwargs[ATTR_TILT_POSITION]
        target = 100 - position
        self.tilt_calc.start_travel(target)
        self.start_auto_updater()
        command = SERVICE_OPEN_COVER if target < (self.tilt_calc.current_position() or 100) else SERVICE_CLOSE_COVER
        await self._async_handle_command(command)

    async def async_stop_cover_tilt(self, **kwargs):
        """Stop the cover tilt."""
        if self._has_tilt_support:
            self.tilt_calc.stop()
            self.stop_auto_updater()
            await self._async_handle_command(SERVICE_STOP_COVER)

    def start_auto_updater(self):
        """Start the autoupdater."""
        if not self._unsubscribe_auto_updater:
            self._unsubscribe_auto_updater = async_track_time_interval(
                self.hass, self.auto_updater_hook, timedelta(seconds=0.1)
            )

    def stop_auto_updater(self):
        """Stop the autoupdater."""
        if self._unsubscribe_auto_updater:
            self._unsubscribe_auto_updater()
            self._unsubscribe_auto_updater = None

    @callback
    def auto_updater_hook(self, now):
        """Update cover position."""
        self.position_calc.update_position(now)
        if self._has_tilt_support:
            self.tilt_calc.update_position(now)
        self.async_write_ha_state()
        if (self.position_calc.position_reached() and 
            (not self._has_tilt_support or self.tilt_calc.position_reached())):
            self.stop_auto_updater()
            self.hass.async_create_task(self.async_stop_cover())

    async def _async_handle_command(self, command):
        """Handle commands to physical cover."""
        if self._cover_entity_id:
            await self.hass.services.async_call(
                "cover", command, {"entity_id": self._cover_entity_id}, False
            )
        else:
            open_service = "turn_off" if command == SERVICE_CLOSE_COVER else "turn_on"
            close_service = "turn_on" if command == SERVICE_CLOSE_COVER else "turn_off"
            
            await self.hass.services.async_call(
                "homeassistant", open_service, 
                {"entity_id": self._open_switch_entity_id}, False
            )
            await self.hass.services.async_call(
                "homeassistant", close_service, 
                {"entity_id": self._close_switch_entity_id}, False
            )
            
            if self._is_button:
                await sleep(1)
                await self.hass.services.async_call(
                    "homeassistant", "turn_off",
                    {"entity_id": self._open_switch_entity_id}, False
                )
                await self.hass.services.async_call(
                    "homeassistant", "turn_off",
                    {"entity_id": self._close_switch_entity_id}, False
                )

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the cover platform."""
    devices = []
    
    for device_id, device_config in config[CONF_DEVICES].items():
        devices.append(CoverTimeBased(
            device_id=device_id,
            name=device_config[CONF_NAME],
            open_switch_entity_id=device_config.get(CONF_OPEN_SWITCH_ENTITY_ID),
            close_switch_entity_id=device_config.get(CONF_CLOSE_SWITCH_ENTITY_ID),
            stop_switch_entity_id=device_config.get(CONF_STOP_SWITCH_ENTITY_ID),
            is_button=device_config[CONF_IS_BUTTON],
            cover_entity_id=device_config.get(CONF_COVER_ENTITY_ID),
            travel_time=device_config.get(CONF_TRAVEL_TIME, DEFAULT_TRAVEL_TIME),
            open_map=device_config.get(CONF_OPEN_MAP),
            close_map=device_config.get(CONF_CLOSE_MAP),
            tilt_open_map=device_config.get(CONF_TILT_OPEN_MAP),
            tilt_close_map=device_config.get(CONF_TILT_CLOSE_MAP),
        ))
    
    async_add_entities(devices)
    
    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(
        SERVICE_SET_KNOWN_POSITION, 
        {vol.Required(ATTR_POSITION): cv.positive_int},
        "async_set_known_position"
    )
    platform.async_register_entity_service(
        SERVICE_SET_KNOWN_TILT_POSITION,
        {vol.Required(ATTR_TILT_POSITION): cv.positive_int},
        "async_set_known_tilt_position"
    )

    async def async_set_known_position(entity, service_call):
        """Set known position service."""
        entity.position_calc.set_position(100 - service_call.data[ATTR_POSITION])
        entity.async_write_ha_state()

    async def async_set_known_tilt_position(entity, service_call):
        """Set known tilt position service."""
        if entity._has_tilt_support:
            entity.tilt_calc.set_position(100 - service_call.data[ATTR_TILT_POSITION])
            entity.async_write_ha_state()