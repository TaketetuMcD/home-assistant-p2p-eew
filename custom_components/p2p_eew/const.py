DOMAIN = "p2p_eew"

# Kept for migration from version 1 entries.
CONF_AREA = "area"
CONF_AREAS = "areas"
CONF_MIN_SCALE = "min_scale"
CONF_NOTIFY_INTENSITY_INCREASE = "notify_intensity_increase"

DEFAULT_MIN_SCALE = -1
DEFAULT_NOTIFY_INTENSITY_INCREASE = True

WS_URL = "wss://api.p2pquake.net/v2/ws"
HISTORY_URL = "https://api.p2pquake.net/v2/history"

EVENT_WARNING = "p2p_eew_warning"
EVENT_UPDATE = "p2p_eew_update"
EVENT_CANCEL = "p2p_eew_cancel"

AUTO_CLEAR_SECONDS = 60
TEST_CLEAR_SECONDS = 15

# WebSocket reconnect recovery.
RECOVERY_LIMIT = 20
RECOVERY_MAX_AGE_SECONDS = 300
