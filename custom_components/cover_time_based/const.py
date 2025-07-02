"""Constants for Cover Time Based integration."""

DOMAIN = "cover_time_based"

# Configuration keys
CONF_OPENING_TIME_MAP = "opening_time_map"
CONF_CLOSING_TIME_MAP = "closing_time_map"
CONF_TILTING_TIME_DOWN = "tilting_time_down"
CONF_TILTING_TIME_UP = "tilting_time_up"
CONF_OPEN_SWITCH_ENTITY_ID = "open_switch_entity_id"
CONF_CLOSE_SWITCH_ENTITY_ID = "close_switch_entity_id"
CONF_STOP_SWITCH_ENTITY_ID = "stop_switch_entity_id"
CONF_IS_BUTTON = "is_button"
CONF_COVER_ENTITY_ID = "cover_entity_id"
CONF_USE_EXISTING_COVER = "use_existing_cover"

# Default values
DEFAULT_TILT_TIME = 5.0

# Services
SERVICE_SET_KNOWN_POSITION = "set_known_position"
SERVICE_SET_KNOWN_TILT_POSITION = "set_known_tilt_position"
SERVICE_OPEN_SLACKS = "open_slacks"
SERVICE_CLOSE_SLACKS = "close_slacks"