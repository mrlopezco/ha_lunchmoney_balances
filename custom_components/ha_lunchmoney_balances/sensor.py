"""Sensor platform for Lunch Money Balances integration."""

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.const import ATTR_ATTRIBUTION

from .const import (
    DOMAIN,
    ATTR_ASSET_ID,
    ATTR_TYPE_NAME,
    ATTR_SUBTYPE_NAME,
    ATTR_INSTITUTION_NAME,
    ATTR_BALANCE_AS_OF,
    ATTR_TO_BASE_CURRENCY,
    ATTR_DISPLAY_NAME,
    DEFAULT_ICON,
    CONF_INVERTED_ASSET_TYPES,
    DEFAULT_INVERTED_ASSET_TYPES,
    NET_WORTH_SENSOR_ID_SUFFIX,
    NET_WORTH_DEVICE_NAME,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)
ATTRIBUTION = "Data provided by Lunch Money"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Lunch Money Balance sensor platform."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    if coordinator.data is None:
        _LOGGER.warning(
            "No data received from coordinator during sensor setup. Skipping entity creation. This might be normal if no assets were found initially."
        )
        return

    entities = []
    for asset_id, asset_data in coordinator.data.items():
        if asset_data:  # Ensure asset_data is not None
            entities.append(
                LunchMoneyBalanceSensor(coordinator, asset_id, config_entry)
            )
        else:
            _LOGGER.warning(
                "Asset data for ID %s is missing or invalid, skipping sensor creation.",
                asset_id,
            )

    # Create Net Worth sensor
    # It can be created even if there are no assets (net worth would be 0)
    entities.append(LunchMoneyNetWorthSensor(coordinator, config_entry))

    if entities:
        async_add_entities(entities, True)
    else:
        _LOGGER.info(
            "No sensor entities created for Lunch Money Balances. This is expected if no assets were found."
        )


class LunchMoneyBalanceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Lunch Money asset balance sensor."""

    _attr_state_class = (
        SensorStateClass.TOTAL
    )  # Or MEASUREMENT, TOTAL might be more apt for balance
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_attribution = ATTRIBUTION
    # The icon can be set here if it's always the same, or dynamically in properties
    # _attr_icon = DEFAULT_ICON # Example if you have a single default icon for all balance sensors

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        asset_id: int,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._asset_id = asset_id
        self._config_entry = config_entry
        # Initial data fetch and attribute setting are handled by _handle_coordinator_update
        # called by CoordinatorEntity logic, and also explicitly called once here.
        self._update_internal_state()

    def _get_asset_data(self):
        """Helper to safely get asset data for the current asset_id from the coordinator."""
        if self.coordinator.data and self._asset_id in self.coordinator.data:
            return self.coordinator.data[self._asset_id]
        return None

    def _update_internal_state(self) -> None:
        """Update internal state attributes based on coordinator data."""
        asset_data = self._get_asset_data()
        if asset_data:
            asset_name = getattr(asset_data, "display_name", None) or getattr(
                asset_data, "name", f"Asset {self._asset_id}"
            )
            self._attr_name = f"{asset_name} Balance"  # Sensor name
            self._attr_unique_id = f"{self._config_entry.entry_id}_{self._asset_id}_balance"  # Unique ID for the sensor entity

            inverted_types = self._config_entry.options.get(
                CONF_INVERTED_ASSET_TYPES, DEFAULT_INVERTED_ASSET_TYPES
            )

            self._attr_native_value = self._parse_balance(
                getattr(asset_data, "balance", None)
            )
            self._attr_native_unit_of_measurement = (
                getattr(asset_data, "currency", None).upper()
                if getattr(asset_data, "currency", None)
                else None
            )

            # Dynamic icon based on asset type (optional example)
            type_name = getattr(asset_data, "type_name", "").lower()
            if "cash" in type_name:
                self._attr_icon = "mdi:cash"
            elif "credit" in type_name:
                self._attr_icon = "mdi:credit-card"
            elif "investment" in type_name:
                self._attr_icon = "mdi:chart-line"
            elif "loan" in type_name:
                self._attr_icon = "mdi:bank-transfer-out"
            else:
                self._attr_icon = DEFAULT_ICON  # Fallback to default icon

            if self._attr_native_value is not None and type_name in inverted_types:
                self._attr_native_value = -self._attr_native_value

        else:  # Asset data not found
            self._attr_name = (
                f"Lunch Money Asset {self._asset_id} Balance (Data Missing)"
            )
            self._attr_unique_id = (
                f"{self._config_entry.entry_id}_{self._asset_id}_balance"
            )
            self._attr_native_value = None
            self._attr_native_unit_of_measurement = None
            self._attr_icon = "mdi:alert-circle-outline"  # Icon indicating an issue

    def _parse_balance(self, balance_str: str | None) -> float | None:
        """Safely parse the balance string to a float."""
        if balance_str is None:
            return None
        try:
            # Using Decimal for precision before converting to float for HA state
            return float(Decimal(balance_str))
        except (InvalidOperation, ValueError, TypeError):
            _LOGGER.error(
                "Could not parse balance '%s' for asset %s", balance_str, self._asset_id
            )
            return None

    @property
    def available(self) -> bool:
        """Return True if entity is available (i.e., data is present in coordinator for this asset)."""
        return super().available and self._get_asset_data() is not None

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return information to link this entity with a device."""
        asset_data = self._get_asset_data()
        if not asset_data:
            return None  # Should not happen if entity is available

        asset_name = getattr(asset_data, "display_name", None) or getattr(
            asset_data, "name", f"Unknown Asset {self._asset_id}"
        )
        asset_type = getattr(asset_data, "type_name", "Unknown Type")
        institution = getattr(asset_data, "institution_name", "N/A")

        return DeviceInfo(
            identifiers={
                (DOMAIN, str(self._asset_id))
            },  # Use str(self._asset_id) for robustness
            name=asset_name,  # Device name
            manufacturer="Lunch Money",
            model=f"Asset ({asset_type})",
            configuration_url="https://my.lunchmoney.app/assets",  # Generic link to assets page
            via_device=(
                DOMAIN,
                self._config_entry.entry_id,
            ),  # Link to config entry device
            # You could add sw_version if lunchable exposes API version or similar
        )

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the state attributes."""
        asset_data = self._get_asset_data()
        if not asset_data:
            return None

        attrs = {
            ATTR_ASSET_ID: self._asset_id,  # Already an int
        }

        # Helper to add attribute if present in asset_data
        def add_attr_if_present(
            attr_key_const, data_key_on_asset_obj, is_numeric=False, is_date=False
        ):
            value = getattr(asset_data, data_key_on_asset_obj, None)
            if value is not None:
                if is_numeric:
                    try:
                        attrs[attr_key_const] = float(Decimal(str(value)))
                    except (InvalidOperation, ValueError, TypeError):
                        _LOGGER.debug(
                            "Could not parse numeric attribute %s: %s",
                            data_key_on_asset_obj,
                            value,
                        )
                        attrs[attr_key_const] = (
                            value  # Store as string if parsing fails
                        )
                elif is_date:
                    try:
                        # Ensure balance_as_of is a valid ISO 8601 string before parsing
                        # The lunchable library might already parse this to a datetime object
                        if isinstance(value, datetime):
                            attrs[attr_key_const] = value.isoformat()
                        elif isinstance(value, str):  # If it's a string from API
                            parsed_date = datetime.fromisoformat(
                                value.replace("Z", "+00:00")
                            )
                            attrs[attr_key_const] = parsed_date.isoformat()
                        else:
                            attrs[attr_key_const] = str(value)
                    except (ValueError, TypeError):
                        _LOGGER.warning(
                            "Could not parse date attribute %s: %s",
                            data_key_on_asset_obj,
                            value,
                        )
                        attrs[attr_key_const] = value  # Store as is if parsing fails
                else:
                    attrs[attr_key_const] = value

        add_attr_if_present(ATTR_TYPE_NAME, "type_name")
        add_attr_if_present(ATTR_SUBTYPE_NAME, "subtype_name")
        add_attr_if_present(ATTR_INSTITUTION_NAME, "institution_name")
        add_attr_if_present(
            ATTR_DISPLAY_NAME, "display_name"
        )  # Assuming 'display_name' is an attribute on lunchable's asset object
        add_attr_if_present(
            ATTR_TO_BASE_CURRENCY, "to_base", is_numeric=True
        )  # API uses 'to_base'
        add_attr_if_present(ATTR_BALANCE_AS_OF, "balance_as_of", is_date=True)

        # Add original name from API if display_name was used for the entity name and they differ
        original_name = getattr(asset_data, "name", None)
        display_name_val = getattr(asset_data, "display_name", None)
        if display_name_val and original_name and display_name_val != original_name:
            attrs["asset_original_name"] = original_name
        elif (
            not display_name_val and original_name
        ):  # If display_name is missing, but name is there
            attrs["asset_original_name"] = original_name

        # Add currency code from native_unit_of_measurement if available
        if self.native_unit_of_measurement:
            attrs["currency_code"] = self.native_unit_of_measurement

        # Add whether this balance was inverted
        inverted_types = self._config_entry.options.get(
            CONF_INVERTED_ASSET_TYPES, DEFAULT_INVERTED_ASSET_TYPES
        )
        asset_type = getattr(asset_data, "type_name", "").lower()
        attrs["balance_inverted"] = asset_type in inverted_types

        return attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_internal_state()  # Update all internal attributes based on new data
        if self._get_asset_data() is None:
            _LOGGER.info(
                "Asset ID %s (Sensor: %s unique_id: %s) no longer found in Lunch Money data. Entity will become unavailable.",
                self._asset_id,
                self.entity_id,
                self.unique_id,
            )
            # The entity will become unavailable due to the `available` property check
        self.async_write_ha_state()  # Inform HA of state change

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return True


# --- Net Worth Sensor ---
class LunchMoneyNetWorthSensor(CoordinatorEntity, SensorEntity):
    """Representation of the total Net Worth from Lunch Money assets."""

    _attr_state_class = SensorStateClass.TOTAL
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_attribution = ATTRIBUTION
    _attr_icon = "mdi:scale-balance"

    def __init__(
        self, coordinator: DataUpdateCoordinator, config_entry: ConfigEntry
    ) -> None:
        """Initialize the Net Worth sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_name = (
            f"{NET_WORTH_DEVICE_NAME} Net Worth"  # Or derive from config_entry title
        )
        self._attr_unique_id = (
            f"{self._config_entry.entry_id}_{NET_WORTH_SENSOR_ID_SUFFIX}"
        )
        self._update_internal_state()  # Initial update

    def _get_user_data(self):
        """Helper to safely get user data from the coordinator."""
        if self.coordinator.data and "user" in self.coordinator.data:
            return self.coordinator.data["user"]
        return None

    def _get_all_asset_data(self) -> dict:
        """Helper to safely get all asset data from the coordinator."""
        if self.coordinator.data and "assets" in self.coordinator.data:
            return self.coordinator.data["assets"]
        return {}

    def _update_internal_state(self) -> None:
        """Update the sensor's state."""
        all_assets = self._get_all_asset_data()
        user_data = self._get_user_data()

        inverted_types = self._config_entry.options.get(
            CONF_INVERTED_ASSET_TYPES, DEFAULT_INVERTED_ASSET_TYPES
        )

        total_net_worth = Decimal("0.0")  # Use Decimal for precision

        if all_assets:
            for asset_data in all_assets.values():
                if not hasattr(asset_data, "to_base") or asset_data.to_base is None:
                    _LOGGER.debug(
                        "Asset %s (%s) missing 'to_base' value, skipping for net worth.",
                        getattr(asset_data, "id", "N/A"),
                        getattr(asset_data, "name", "N/A"),
                    )
                    continue

                try:
                    # Ensure to_base is treated as a string for Decimal conversion if it's float/int
                    base_value = Decimal(str(asset_data.to_base))
                    asset_type = getattr(asset_data, "type_name", "").lower()

                    if asset_type in inverted_types:
                        total_net_worth -= base_value
                    else:
                        total_net_worth += base_value
                except (InvalidOperation, ValueError, TypeError) as e:
                    _LOGGER.error(
                        "Error processing to_base value '%s' for asset %s for net worth: %s",
                        asset_data.to_base,
                        getattr(asset_data, "id", "N/A"),
                        e,
                    )

        self._attr_native_value = float(
            total_net_worth
        )  # Convert to float for HA state

        if user_data and hasattr(user_data, "currency") and user_data.currency:
            self._attr_native_unit_of_measurement = user_data.currency.upper()
        else:
            # Try to infer from first asset with a 'to_base' and 'currency' if user_data is missing currency
            # This is a fallback, primary should be user_data.currency
            self._attr_native_unit_of_measurement = (
                None  # Default to None if not determinable
            )
            if all_assets:
                for asset_data in all_assets.values():
                    if (
                        hasattr(asset_data, "to_base")
                        and asset_data.to_base is not None
                        and hasattr(asset_data, "currency")
                        and asset_data.currency
                    ):
                        # This assumes the 'currency' of an asset might reflect the base currency,
                        # which is not strictly true. user_data.currency is the correct source.
                        # self._attr_native_unit_of_measurement = asset_data.currency.upper()
                        # break
                        pass  # Keep it None, rely on user_data.currency only

    @property
    def available(self) -> bool:
        """Return True if entity is available (i.e., coordinator has data)."""
        # Net worth sensor is available as long as the coordinator has run once,
        # even if there are no assets (net worth would be 0).
        # It primarily depends on the 'user' part for currency.
        return (
            super().available
            and self.coordinator.data is not None
            and "user" in self.coordinator.data
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return information for the Net Worth device."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, f"{self._config_entry.entry_id}_summary")
            },  # Unique ID for this summary device
            name=NET_WORTH_DEVICE_NAME,
            manufacturer="Lunch Money",
            model="Account Summary",
            via_device=(
                DOMAIN,
                self._config_entry.entry_id,
            ),  # Links it to the main config entry device
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_internal_state()
        self.async_write_ha_state()

    @property
    def entity_registry_enabled_default(self) -> bool:
        return True
