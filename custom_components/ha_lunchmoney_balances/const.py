"""Constants for the Lunch Money Balances integration."""

# This is the most important part to match your folder and intended domain
DOMAIN = "ha_lunchmoney_balances"

# Configuration constants
CONF_API_KEY = "api_key"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_INVERTED_ASSET_TYPES = "inverted_asset_types"

# Default values
DEFAULT_UPDATE_INTERVAL = 720  # 12 hours in minutes
DEFAULT_INVERTED_ASSET_TYPES = ["credit", "loan"]

# Update interval options mapping
UPDATE_INTERVAL_OPTIONS = {
    720: "Twice a day (every 12 hours)",
    1440: "Daily (every 24 hours)",
}

# Asset types - used for configuration. Add more if Lunch Money has more.
# These should ideally match the 'type_name' values from the API.
# From your sample: "cash", "credit", "vehicle", "loan", "real estate", "investment", "employee compensation"
POSSIBLE_ASSET_TYPES = sorted(
    [
        "cash",
        "credit",
        "loan",
        "investment",
        "real estate",
        "vehicle",
        "employee compensation",
        "other assets",  # General categories if API uses them
        "other liabilities",
    ]
)

# Attributes for the Lunch Money sensors
ATTR_ASSET_ID = "asset_id"
ATTR_TYPE_NAME = "type_name"
ATTR_SUBTYPE_NAME = "subtype_name"
ATTR_INSTITUTION_NAME = "institution_name"
ATTR_BALANCE_AS_OF = "balance_as_of"
ATTR_TO_BASE_CURRENCY = "to_base_currency"
ATTR_DISPLAY_NAME = "display_name"

# Net Worth Sensor
NET_WORTH_SENSOR_ID_SUFFIX = "net_worth"
NET_WORTH_DEVICE_NAME = "Lunch Money Summary"

# Platforms to set up
PLATFORMS = ["sensor"]

# Default icon
DEFAULT_ICON = "mdi:cash-multiple"

# The constants below are not used by the Lunch Money integration as specified in your initial request.
# DOMAIN_DATA = f"{DOMAIN}_data" # This is a common pattern, but the coordinator stores data in hass.data[DOMAIN][entry_id]
# CONFIG_ENDPOINT = "endpoint"
# CONFIG_PASSWORD = "password"
# CONFIG_FILE = "file"
# CONFIG_UNIT = "unit"
# CONFIG_PREFIX = "prefix"
# CONFIG_CERT = "cert"
# CONFIG_ENCRYPT_PASSWORD = "encrypt_password"
