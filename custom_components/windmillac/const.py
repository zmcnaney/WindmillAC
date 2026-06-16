"""Constants for Windmill AC."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "WindmillAC"
DOMAIN = "windmillac"
VERSION = "1.1.0"
UPDATE_INTERVAL = 60
CONF_TOKEN = "token"
BASE_URL = "https://dashboard.windmillair.com"

PRODUCT_AC = "ac"
PRODUCT_FAN = "fan"

PLATFORMS_BY_PRODUCT = {
    PRODUCT_AC: ["climate"],
    PRODUCT_FAN: ["fan"],
}

FAN_ORDERED_SPEEDS = ["1", "2", "3", "4", "5"]
