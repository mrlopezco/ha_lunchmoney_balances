"""Constants for the Lunch Money Balances integration."""

# This is the most important part to match your folder and intended domain
DOMAIN = "ha_lunchmoney_balances"

# Configuration constants relevant to Lunch Money as per your requirements
CONF_API_KEY = "api_key"
CONF_UPDATE_INTERVAL = "update_interval"

# Default values for Lunch Money
DEFAULT_UPDATE_INTERVAL = 720  # Default to 12 hours (720 minutes)

# Update interval options mapping (value_in_minutes: "User Friendly Name")
# These are for the Lunch Money integration
UPDATE_INTERVAL_OPTIONS = {
    720: "Twice a day (every 12 hours)",
    1440: "Daily (every 24 hours)",
}

# Attributes for the Lunch Money sensors
ATTR_ASSET_ID = "asset_id"
ATTR_TYPE_NAME = "type_name"
ATTR_SUBTYPE_NAME = "subtype_name"
ATTR_INSTITUTION_NAME = "institution_name"
ATTR_BALANCE_AS_OF = "balance_as_of"
ATTR_TO_BASE_CURRENCY = "to_base_currency"  # Renamed from "to_base" for clarity
ATTR_DISPLAY_NAME = "display_name"

# Platforms to set up
PLATFORMS = ["sensor"]

# Optional: Default icon for entities if not specified elsewhere
DEFAULT_ICON = "mdi:cash-multiple"  # Icon for currency/assets

# The constants below are not used by the Lunch Money integration as specified in your initial request.
# DOMAIN_DATA = f"{DOMAIN}_data" # This is a common pattern, but the coordinator stores data in hass.data[DOMAIN][entry_id]
# CONFIG_ENDPOINT = "endpoint"
# CONFIG_PASSWORD = "password"
# CONFIG_FILE = "file"
# CONFIG_UNIT = "unit"
# CONFIG_PREFIX = "prefix"
# CONFIG_CERT = "cert"
# CONFIG_ENCRYPT_PASSWORD = "encrypt_password"
