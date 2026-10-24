"""Constants for the Elon Smart Water integration."""

DOMAIN = "elon_smart_water"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_NETWORK = "network"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_APPLICATION_ID = "application_id"
CONF_AUTH_ID = "auth_id"

DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = 60  # seconds

# Status read path (works unauthenticated on the local port).
API_PATH = "/V1/DeviceStatus/Query"
API_TIMEOUT = 10  # seconds

# Control paths, confirmed against a capture of the official app. Each body is
# {"applicationId": int, "authId": str, "deviceSerial": int} and the device
# answers {"status": "Success"}.
PATH_FORCE_REHEAT = "/V1/Thermostat/ForceReheat"  # PUT
PATH_CANCEL_GRID_HEATING = "/V1/Thermostat/CancelGridHeating"  # PUT

SCAN_TIMEOUT = 3  # seconds per host during network scan
MAX_CONCURRENT_SCANS = 50  # maximum concurrent scan connections
