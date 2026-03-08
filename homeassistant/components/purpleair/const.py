"""Constants for the PurpleAir integration."""

import logging
from typing import Final

DOMAIN: Final[str] = "purpleair"
LOGGER: Final[logging.Logger] = logging.getLogger(DOMAIN)
TITLE: Final[str] = "PurpleAir"
SCHEMA_VERSION: Final[int] = 2

CONF_ADD_MAP_LOCATION: Final = "add_map_location"
CONF_ADD_OPTIONS: Final = "add_options"
CONF_ADD_SENSOR_INDEX: Final = "add_sensor_index"
CONF_NO_SENSOR_FOUND: Final = "no_sensor_found"
CONF_NO_SENSORS_FOUND: Final = "no_sensors_found"
CONF_SELECT_SENSOR: Final = "select_sensor"
CONF_SENSOR_INDEX: Final = "sensor_index"
CONF_SENSOR_READ_KEY: Final = "sensor_read_key"
CONF_SENSOR: Final = "sensor"
SUBENTRY_TYPE_SENSOR: Final = "sensor"
CONF_SETTINGS: Final = "settings"
CONF_UNKNOWN: Final = "unknown"

SENSOR_FIELDS_ALL: Final[list[str]] = [
    "0.3_um_count",
    "0.5_um_count",
    "1.0_um_count",
    "10.0_um_count",
    "2.5_um_count",
    "5.0_um_count",
    "altitude",
    "firmware_version",
    "hardware",
    "humidity",
    "latitude",
    "location_type",
    "longitude",
    "model",
    "name",
    "pm1.0",
    "pm10.0",
    "pm2.5",
    "pressure",
    "rssi",
    "temperature",
    "uptime",
    "voc",
]
