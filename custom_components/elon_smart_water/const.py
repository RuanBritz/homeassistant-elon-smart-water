"""Constants for the Elon Smart Water integration."""

DOMAIN = "elon_smart_water"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_NETWORK = "network"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = 60  # seconds

API_PATH = "/V1/DeviceStatus/Query"
API_FORCE_REHEAT_PATH = "/V1/Thermostat/ForceReheat"
API_CANCEL_GRID_HEATING_PATH = "/V1/Thermostat/CancelGridHeating"
API_TIMEOUT = 10  # seconds

SCAN_TIMEOUT = 3  # seconds per host during network scan
MAX_CONCURRENT_SCANS = 50  # maximum concurrent scan connections
