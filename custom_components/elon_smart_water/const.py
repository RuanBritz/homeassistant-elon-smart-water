"""Constants for the Elon Smart Water integration."""

DOMAIN = "elon_smart_water"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_NETWORK = "network"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = 60  # seconds

API_PATH = "/V1/DeviceStatus/Query"
API_MEASUREMENTS_PATH = "/V1/Measurements/Query"
API_CONFIG_PATH = "/V1/DeviceConfiguration/Property/Query"
API_TIMEOUT = 10  # seconds

SENSOR_ID_SOLAR_INPUT = 110
SENSOR_ID_ELEMENT_POWER = 109
CONFIG_PROPERTIES = ["HeatingPolicy", "SolarSetPoint", "GridSetPoint"]
MEASUREMENTS_WINDOW = 7200  # seconds - query last 2 hours of measurements

SCAN_TIMEOUT = 3  # seconds per host during network scan
MAX_CONCURRENT_SCANS = 50  # maximum concurrent scan connections
