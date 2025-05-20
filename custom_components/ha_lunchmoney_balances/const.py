"""Constants for the Lunch Money Balances integration."""

# This is the most important part to match your folder and intended domain
DOMAIN = "ha_lunchmoney_balances"

# Configuration constants
CONF_API_KEY = "api_key"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_INVERTED_ASSET_TYPES = "inverted_asset_types"
CONF_PRIMARY_CURRENCY = (
    "primary_currency"  # New: Primary currency for net worth calculation
)

# Default values
DEFAULT_UPDATE_INTERVAL = 720  # 12 hours in minutes
DEFAULT_INVERTED_ASSET_TYPES = ["credit", "loan"]

# Update interval options mapping
UPDATE_INTERVAL_OPTIONS = {
    720: "Twice a day (every 12 hours)",
    1440: "Daily (every 24 hours)",
}

# Asset types - used for configuration.
# These should cover 'type_name' from manual assets and 'type' from Plaid accounts.
# Example Plaid types: "depository" (checking/savings), "credit card", "loan", "investment", "brokerage"
# The 'type' field from PlaidAccountObject is just 'type', not 'type_name'.
POSSIBLE_ASSET_TYPES = sorted(
    list(
        set(
            [  # Use set to avoid duplicates
                "cash",
                "credit",  # Covers Plaid "credit card" if mapped
                "loan",
                "investment",  # Covers Plaid "investment", "brokerage"
                "real estate",
                "vehicle",
                "employee compensation",
                "depository",  # From Plaid (checking, savings)
                "brokerage",  # From Plaid
                "other",  # General fallback from Plaid or manual
                # Add any other distinct types you see from Plaid or manual assets
            ]
        )
    )
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
