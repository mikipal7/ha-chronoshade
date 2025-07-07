"""Constants for ChronoShade integration."""

DOMAIN = "chronoshade"

# Configuration keys
CONF_OPENING_TIME_MAP = "opening_time_map"
CONF_CLOSING_TIME_MAP = "closing_time_map"
CONF_OPENING_TIME = "opening_time"
CONF_CLOSING_TIME = "closing_time"
CONF_TILTING_TIME_DOWN = "tilting_time_down"
CONF_TILTING_TIME_UP = "tilting_time_up"
CONF_OPEN_SWITCH_ENTITY_ID = "open_switch_entity_id"
CONF_CLOSE_SWITCH_ENTITY_ID = "close_switch_entity_id"
CONF_STOP_SWITCH_ENTITY_ID = "stop_switch_entity_id"
CONF_IS_BUTTON = "is_button"
CONF_COVER_ENTITY_ID = "cover_entity_id"
CONF_CONTROL_METHOD = "control_method"
CONF_DEVICE_CLASS = "device_class"

# Control methods
CONTROL_METHOD_SWITCHES = "switches"
CONTROL_METHOD_EXISTING_COVER = "existing_cover"

# Default values
DEFAULT_TILT_TIME = 5.0
DEFAULT_OPENING_TIME_MAP = {0.0: 0, 10.0: 100}
DEFAULT_CLOSING_TIME_MAP = {0.0: 100, 10.0: 0}

# Services
SERVICE_SET_KNOWN_POSITION = "set_known_position"
SERVICE_SET_KNOWN_TILT_POSITION = "set_known_tilt_position"

# Device info
MANUFACTURER = "ChronoShade"
MODEL = "Precision Time-based Cover Controller"

# Migration
CURRENT_CONFIG_VERSION = 4