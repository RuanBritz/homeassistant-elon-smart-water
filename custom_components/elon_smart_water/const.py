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

# Control paths on the thermostat's local HTTP API. These, and the JSON field
# names below, were recovered from the app's compiled request builders in
# libapp.so (see API_ENDPOINTS.md). Every local request body carries
# applicationId, authId and (per device) deviceSerial as integers.
PATH_FORCE_REHEAT = "/V1/Thermostat/ForceReheat"  # PUT
PATH_CANCEL_GRID_HEATING = "/V1/Thermostat/CancelGridHeating"  # PUT
PATH_PROPERTY_UPDATE = "/V1/DeviceConfiguration/Property/Update"  # PUT
PATH_PROPERTY_QUERY = "/V1/DeviceConfiguration/Property/Query"  # PUT

# Property names used by Property/Update.
PROP_HEATING_POLICY = "HeatingPolicy"
PROP_SOLAR_SETPOINT = "SolarSetPoint"
PROP_GRID_SETPOINT = "GridSetPoint"

# HeatingPolicy values as seen in the app's own debug screen.
HEATING_POLICY_SOLAR_ONLY = 1
HEATING_POLICY_GRID_ONLY = 5
HEATING_POLICY_OPTIONS: dict[str, int] = {
    "Solar Only": HEATING_POLICY_SOLAR_ONLY,
    "Grid Only": HEATING_POLICY_GRID_ONLY,
}

# Setpoint bounds (deg C) for the number entities. Conservative defaults; the
# device clamps to its own supported range.
MIN_SETPOINT = 20
MAX_SETPOINT = 70

SCAN_TIMEOUT = 3  # seconds per host during network scan
MAX_CONCURRENT_SCANS = 50  # maximum concurrent scan connections
