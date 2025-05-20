"""Sensor platform for Lunch Money Balances integration."""

import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Set

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
from homeassistant.util import dt as dt_util

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

# Epsilon for floating point comparisons to zero
ZERO_BALANCE_EPSILON = 1e-6


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Lunch Money Balance sensor platform."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Store the add_entities callback and a dictionary to track active sensors
    # This allows the coordinator update listener to dynamically add/remove entities
    hass.data[DOMAIN].setdefault("active_balance_sensors", {})
    hass.data[DOMAIN].setdefault(
        "active_currency_net_worth_sensors", {}
    )  # New: for currency net worth sensors
    hass.data[DOMAIN]["add_balance_entities_callback"] = async_add_entities

    _LOGGER.debug("Sensor setup: Full coordinator data: %s", coordinator.data)

    # Add the Net Worth sensor directly, as it's always present
    _LOGGER.debug("Sensor setup: Creating LunchMoneyNetWorthSensor.")
    async_add_entities([LunchMoneyNetWorthSensor(coordinator, config_entry)], True)

    # Register the listener for coordinator updates
    # This listener will handle dynamic creation/removal of individual balance sensors
    @callback
    def _async_coordinator_update_listener():
        """Handle updated data from the coordinator and manage balance sensors."""
        _LOGGER.debug("Coordinator update listener triggered.")
        current_data = coordinator.data

        if current_data is None or (
            "manual_assets" not in current_data and "plaid_accounts" not in current_data
        ):
            _LOGGER.warning(
                "Coordinator data is missing or not structured correctly in listener: %s",
                current_data,
            )
            return

        active_balance_sensors: Dict[str, LunchMoneyBalanceSensor] = hass.data[DOMAIN][
            "active_balance_sensors"
        ]
        active_currency_net_worth_sensors: Dict[
            str, LunchMoneyNetWorthCurrencySensor
        ] = hass.data[DOMAIN][
            "active_currency_net_worth_sensors"
        ]  # New
        add_entities_callback: AddEntitiesCallback = hass.data[DOMAIN][
            "add_balance_entities_callback"
        ]

        desired_balance_entity_ids: Set[str] = set()
        desired_currency_net_worth_entity_ids: Set[str] = set()  # New
        entities_to_add = []

        # Collect all unique currencies for currency-specific net worth sensors
        all_currencies: Set[str] = set()

        # Process manual assets
        manual_assets_dict = current_data.get("manual_assets", {})
        for asset_id, asset_data in manual_assets_dict.items():
            # Calculate effective balance for manual assets
            raw_balance_str = getattr(asset_data, "balance", None)
            parsed_balance = None
            if raw_balance_str is not None:
                try:
                    parsed_balance = float(Decimal(str(raw_balance_str)))
                except (InvalidOperation, ValueError, TypeError):
                    _LOGGER.error(
                        "Could not parse balance string '%s' for manual asset %s",
                        raw_balance_str,
                        asset_id,
                    )

            # Determine if balance is effectively zero
            is_zero_balance = (
                parsed_balance is None or abs(parsed_balance) < ZERO_BALANCE_EPSILON
            )

            unique_id = f"{config_entry.entry_id}_manual_{asset_id}_balance"
            desired_balance_entity_ids.add(unique_id)

            if not is_zero_balance and unique_id not in active_balance_sensors:
                # Balance is non-zero and sensor not yet created, so create it
                _LOGGER.debug(
                    "Adding new LunchMoneyBalanceSensor for manual asset_id: %s (balance: %s)",
                    asset_id,
                    parsed_balance,
                )
                new_sensor = LunchMoneyBalanceSensor(
                    coordinator, asset_id, config_entry, is_plaid=False
                )
                entities_to_add.append(new_sensor)
                active_balance_sensors[unique_id] = new_sensor
            elif is_zero_balance and unique_id in active_balance_sensors:
                # Balance is zero and sensor exists, so mark for removal
                _LOGGER.debug(
                    "Marking LunchMoneyBalanceSensor for manual asset_id: %s for removal (balance: %s)",
                    asset_id,
                    parsed_balance,
                )
                pass  # Handled in the removal loop below

            # Collect currency for currency-specific net worth
            currency = getattr(asset_data, "currency", None)
            if currency:
                all_currencies.add(currency.upper())

        # Process Plaid accounts
        plaid_accounts_dict = current_data.get("plaid_accounts", {})
        for account_id, account_data in plaid_accounts_dict.items():
            # Balance for Plaid is already float or None
            raw_balance = getattr(account_data, "balance", None)

            # Determine if balance is effectively zero
            is_zero_balance = (
                raw_balance is None or abs(raw_balance) < ZERO_BALANCE_EPSILON
            )

            unique_id = f"{config_entry.entry_id}_plaid_{account_id}_balance"
            desired_balance_entity_ids.add(unique_id)

            if not is_zero_balance and unique_id not in active_balance_sensors:
                # Balance is non-zero and sensor not yet created, so create it
                _LOGGER.debug(
                    "Adding new LunchMoneyBalanceSensor for Plaid account_id: %s (balance: %s)",
                    account_id,
                    raw_balance,
                )
                new_sensor = LunchMoneyBalanceSensor(
                    coordinator, account_id, config_entry, is_plaid=True
                )
                entities_to_add.append(new_sensor)
                active_balance_sensors[unique_id] = new_sensor
            elif is_zero_balance and unique_id in active_sensors:
                # Balance is zero and sensor exists, so mark for removal
                _LOGGER.debug(
                    "Marking LunchMoneyBalanceSensor for Plaid account_id: %s for removal (balance: %s)",
                    account_id,
                    raw_balance,
                )
                pass  # Handled in the removal loop below

            # Collect currency for currency-specific net worth
            currency = getattr(account_data, "currency", None)
            if currency:
                all_currencies.add(currency.upper())

        # Add new individual balance entities
        if entities_to_add:
            _LOGGER.debug(
                "Adding %d new balance sensor entities.", len(entities_to_add)
            )
            add_entities_callback(entities_to_add, True)

        # Remove individual balance entities that are no longer desired (balance became zero)
        entities_to_remove = []
        for unique_id, sensor_instance in list(
            active_balance_sensors.items()
        ):  # Iterate over a copy
            if unique_id not in desired_balance_entity_ids:
                _LOGGER.debug("Removing balance sensor entity: %s", unique_id)
                entities_to_remove.append(sensor_instance)
                del active_balance_sensors[unique_id]  # Remove from our tracking dict

        for sensor_instance in entities_to_remove:
            if sensor_instance.hass:  # Ensure it's still attached to Home Assistant
                sensor_instance.async_remove(
                    force_remove=True
                )  # Force remove from HA registry

        # Update existing individual balance entities (those that remain active)
        for sensor_instance in active_balance_sensors.values():
            sensor_instance.async_write_ha_state()  # Trigger state update for existing sensors

        # --- Manage Currency-specific Net Worth Sensors ---
        currency_net_worth_entities_to_add = []
        for currency_code in all_currencies:
            unique_id = f"{config_entry.entry_id}_{NET_WORTH_SENSOR_ID_SUFFIX}_{currency_code.lower()}"
            desired_currency_net_worth_entity_ids.add(unique_id)

            if unique_id not in active_currency_net_worth_sensors:
                _LOGGER.debug(
                    "Adding new LunchMoneyNetWorthCurrencySensor for currency: %s",
                    currency_code,
                )
                new_sensor = LunchMoneyNetWorthCurrencySensor(
                    coordinator, config_entry, currency_code
                )
                currency_net_worth_entities_to_add.append(new_sensor)
                active_currency_net_worth_sensors[unique_id] = new_sensor

        if currency_net_worth_entities_to_add:
            _LOGGER.debug(
                "Adding %d new currency net worth sensor entities.",
                len(currency_net_worth_entities_to_add),
            )
            add_entities_callback(currency_net_worth_entities_to_add, True)

        currency_entities_to_remove = []
        for unique_id, sensor_instance in list(
            active_currency_net_worth_sensors.items()
        ):
            if unique_id not in desired_currency_net_worth_entity_ids:
                _LOGGER.debug(
                    "Removing currency net worth sensor entity: %s", unique_id
                )
                currency_entities_to_remove.append(sensor_instance)
                del active_currency_net_worth_sensors[unique_id]

        for sensor_instance in currency_entities_to_remove:
            if sensor_instance.hass:
                sensor_instance.async_remove(force_remove=True)

        for sensor_instance in active_currency_net_worth_sensors.values():
            sensor_instance.async_write_ha_state()  # Trigger state update for existing sensors

    # Add the listener to the coordinator
    coordinator.async_add_listener(_async_coordinator_update_listener)

    # Run the listener once immediately to set up initial sensors
    _async_coordinator_update_listener()

    # The rest of async_setup_entry remains the same
    # ... (no changes below this point in init.py)


class LunchMoneyBalanceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Lunch Money asset or Plaid account balance sensor."""

    _attr_state_class = SensorStateClass.TOTAL
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        item_id: int,
        config_entry: ConfigEntry,
        is_plaid: bool,
    ) -> None:
        """Initialize the sensor for a manual asset or Plaid account."""
        super().__init__(coordinator)
        self._item_id = item_id  # This is asset.id or plaid_account.id
        self._config_entry = config_entry
        self._is_plaid = is_plaid
        self._item_type_prefix = "plaid" if is_plaid else "manual"
        # Initial update of internal state, but availability is now managed by add/remove logic
        self._update_internal_state()

    def _get_item_data(
        self,
    ) -> Any | None:  # Any can be AssetsObject or PlaidAccountObject
        """Helper to safely get item data from the coordinator."""
        data_key = "plaid_accounts" if self._is_plaid else "manual_assets"
        if (
            self.coordinator.data
            and data_key in self.coordinator.data
            and self._item_id in self.coordinator.data[data_key]
        ):
            return self.coordinator.data[data_key][self._item_id]
        # _LOGGER.debug( # This debug log can be noisy if entities are frequently not found
        #     "_get_item_data: Item ID %s (type: %s) not found in coordinator's %s dict.",
        #     self._item_id,
        #     self._item_type_prefix,
        #     data_key,
        # )
        return None

    def _update_internal_state(self) -> None:
        """Update internal state attributes based on coordinator data."""
        item_data = self._get_item_data()

        inverted_types_config = self._config_entry.options.get(
            CONF_INVERTED_ASSET_TYPES, DEFAULT_INVERTED_ASSET_TYPES
        )

        if item_data:
            item_name: str
            raw_balance_val: float | None
            currency_val: str | None
            item_type_for_inversion: str  # Used to check against inverted_types_config

            if self._is_plaid:
                # PlaidAccountObject attributes
                item_name = getattr(item_data, "name", f"Plaid Account {self._item_id}")
                # balance is Optional[float], so it can be None
                raw_balance_val = getattr(item_data, "balance", None)
                currency_val = getattr(item_data, "currency", None)
                item_type_for_inversion = getattr(
                    item_data, "type", ""
                ).lower()  # Plaid uses 'type'
            else:
                # AssetsObject attributes (manual asset)
                item_name = getattr(item_data, "display_name", None) or getattr(
                    item_data, "name", f"Asset {self._item_id}"
                )
                raw_balance_val = self._parse_balance(
                    getattr(item_data, "balance", None)
                )  # Manual balance is string
                currency_val = getattr(item_data, "currency", None)
                item_type_for_inversion = getattr(
                    item_data, "type_name", ""
                ).lower()  # Manual uses 'type_name'

            self._attr_name = f"{item_name} Balance"
            # Unique ID is critical for dynamic management, must match the one used in listener
            self._attr_unique_id = f"{self._config_entry.entry_id}_{self._item_type_prefix}_{self._item_id}_balance"

            if (
                raw_balance_val is not None
                and item_type_for_inversion in inverted_types_config
            ):
                self._attr_native_value = -raw_balance_val
            else:
                self._attr_native_value = raw_balance_val

            self._attr_native_unit_of_measurement = (
                currency_val.upper() if currency_val else None
            )

            # Icon logic (can be expanded for Plaid specific types if needed)
            icon_type_source = (
                item_type_for_inversion  # Use the already determined type
            )
            if "cash" in icon_type_source or "depository" in icon_type_source:
                self._attr_icon = "mdi:cash"
            elif "credit" in icon_type_source:
                self._attr_icon = "mdi:credit-card"
            elif "investment" in icon_type_source or "brokerage" in icon_type_source:
                self._attr_icon = "mdi:chart-line"
            elif "loan" in icon_type_source:
                self._attr_icon = "mdi:bank-transfer-out"
            else:
                self._attr_icon = DEFAULT_ICON
        else:
            # If item_data is None, it means the item is no longer in the coordinator data
            # This sensor instance should be removed by the listener, but for safety
            # we can set attributes to None or a default "missing" state.
            # In this dynamic add/remove model, this branch should ideally not be hit
            # for active sensors, as they would have been removed already.
            self._attr_name = f"Lunch Money Item {self._item_type_prefix} {self._item_id} Balance (Data Missing)"
            self._attr_unique_id = f"{self._config_entry.entry_id}_{self._item_type_prefix}_{self._item_id}_balance"
            self._attr_native_value = None
            self._attr_native_unit_of_measurement = None
            self._attr_icon = "mdi:alert-circle-outline"

    def _parse_balance(self, balance_str: str | None) -> float | None:
        """Safely parse the balance string (from manual assets) to a float."""
        if balance_str is None:
            return None
        try:
            return float(Decimal(balance_str))
        except (InvalidOperation, ValueError, TypeError):
            _LOGGER.error(
                "Could not parse balance string '%s' for item %s",
                balance_str,
                self._item_id,
            )
            return None

    @property
    def available(self) -> bool:
        """Sensor is always available if it's been added to Home Assistant."""
        # Availability is now managed by the dynamic add/remove logic in the listener.
        # If the sensor exists, it means its balance was non-zero.
        return super().available

    @property
    def device_info(self) -> DeviceInfo | None:
        item_data = self._get_item_data()
        if not item_data:
            # If item_data is None, the sensor should ideally be removed by the listener.
            # Return None to indicate no device info if data is genuinely missing.
            return None

        device_identifier_suffix = f"{self._item_type_prefix}_{self._item_id}"
        device_name: str
        model_type: str

        if self._is_plaid:
            device_name = getattr(item_data, "name", f"Plaid Account {self._item_id}")
            model_type = getattr(item_data, "type", "N/A")  # Plaid uses 'type'
        else:
            device_name = getattr(item_data, "display_name", None) or getattr(
                item_data, "name", f"Asset {self._item_id}"
            )
            model_type = getattr(
                item_data, "type_name", "N/A"
            )  # Manual uses 'type_name'

        _LOGGER.debug(
            "Device Info for Item ID %s (Type: %s): Name: %s",
            self._item_id,
            self._item_type_prefix,
            device_name,
        )

        return DeviceInfo(
            identifiers={(DOMAIN, device_identifier_suffix)},
            name=device_name,
            manufacturer="Lunch Money",
            model=f"{('Plaid Account' if self._is_plaid else 'Manual Asset')} ({model_type})",
            configuration_url="https://my.lunchmoney.app/"
            + ("plaid" if self._is_plaid else "assets"),
            via_device=(DOMAIN, self._config_entry.entry_id),
            icon="mdi:currency-usd",  # Added dollar icon
        )

    @property
    def extra_state_attributes(self) -> dict | None:
        item_data = self._get_item_data()
        if not item_data:
            return None

        attrs = {
            ATTR_ASSET_ID: self._item_id,  # This is the LunchMoney internal ID for the asset/plaid_account
            "item_source": "plaid" if self._is_plaid else "manual",
        }

        # Adapt attribute fetching based on item_data type (Plaid or Manual)
        if self._is_plaid:
            attrs["plaid_account_type"] = getattr(item_data, "type", None)
            attrs["plaid_account_subtype"] = getattr(item_data, "subtype", None)
            attrs["institution_name"] = getattr(item_data, "institution_name", None)
            attrs["plaid_mask"] = getattr(item_data, "mask", None)
            attrs["plaid_status"] = getattr(item_data, "status", None)
            balance_as_of_val = getattr(
                item_data, "balance_last_update", None
            )  # datetime object
        else:  # Manual Asset
            attrs["asset_type_name"] = getattr(item_data, "type_name", None)
            attrs["asset_subtype_name"] = getattr(item_data, "subtype_name", None)
            attrs["institution_name"] = getattr(item_data, "institution_name", None)
            # Manual 'to_base' is important if it exists
            to_base_val = getattr(item_data, "to_base", None)
            if to_base_val is not None:
                try:
                    attrs["to_base_currency_value"] = float(Decimal(str(to_base_val)))
                except (InvalidOperation, ValueError, TypeError):
                    _LOGGER.error(
                        "Could not parse to_base_currency_value '%s' for manual asset %s",
                        to_base_val,
                        self._item_id,
                    )
                    attrs["to_base_currency_value"] = None  # Set to None on error
            balance_as_of_val = getattr(
                item_data, "balance_as_of", None
            )  # str or datetime

        # Common formatting for balance_as_of
        if balance_as_of_val:
            if isinstance(balance_as_of_val, datetime):
                attrs["balance_as_of"] = balance_as_of_val.isoformat()
            elif isinstance(balance_as_of_val, str):
                try:
                    attrs["balance_as_of"] = datetime.fromisoformat(
                        balance_as_of_val.replace("Z", "+00:00")
                    ).isoformat()
                except ValueError:
                    attrs["balance_as_of"] = balance_as_of_val
            elif isinstance(balance_as_of_val, date):  # Plaid date_linked might be date
                attrs["balance_as_of"] = balance_as_of_val.isoformat()

        if self.native_unit_of_measurement:
            attrs["currency_code"] = self.native_unit_of_measurement

        inverted_types_config = self._config_entry.options.get(
            CONF_INVERTED_ASSET_TYPES, DEFAULT_INVERTED_ASSET_TYPES
        )
        item_type_for_inversion = getattr(
            item_data, "type" if self._is_plaid else "type_name", ""
        ).lower()
        attrs["balance_inverted"] = item_type_for_inversion in inverted_types_config

        # Add original name for manual assets if display_name was used
        if not self._is_plaid:
            original_name = getattr(item_data, "name", None)
            display_name_val = getattr(item_data, "display_name", None)
            if display_name_val and original_name and display_name_val != original_name:
                attrs["asset_original_name"] = original_name
            elif not display_name_val and original_name:
                attrs["asset_original_name"] = original_name
        elif self._is_plaid:  # For Plaid, name is the primary identifier
            attrs["plaid_account_name"] = getattr(item_data, "name", None)

        return attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator.
        This method is called when the coordinator updates.
        The actual adding/removing of entities is handled by the listener in async_setup_entry.
        This method just ensures the state of *this* sensor instance is updated.
        """
        self._update_internal_state()
        self.async_write_ha_state()

    @property
    def entity_registry_enabled_default(self) -> bool:
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

    def _get_manual_asset_data(self) -> dict:
        if self.coordinator.data and "manual_assets" in self.coordinator.data:
            return self.coordinator.data["manual_assets"]
        return {}

    def _get_plaid_account_data(self) -> dict:
        if self.coordinator.data and "plaid_accounts" in self.coordinator.data:
            return self.coordinator.data["plaid_accounts"]
        return {}

    def _update_internal_state(self) -> None:
        """Update the sensor's state, summing from manual and Plaid accounts."""
        manual_assets = self._get_manual_asset_data()
        plaid_accounts = self._get_plaid_account_data()
        user_data = self._get_user_data()

        inverted_types_config = self._config_entry.options.get(
            CONF_INVERTED_ASSET_TYPES, DEFAULT_INVERTED_ASSET_TYPES
        )

        total_net_worth = Decimal("0.0")
        user_primary_currency = getattr(user_data, "currency", None)
        if user_primary_currency:
            user_primary_currency = user_primary_currency.lower()

        # Sum from manual assets (using 'to_base')
        for asset_data in manual_assets.values():
            if not hasattr(asset_data, "to_base") or asset_data.to_base is None:
                _LOGGER.debug(
                    "Manual Asset %s (%s) missing 'to_base', skipping for net worth.",
                    getattr(asset_data, "id", "N/A"),
                    getattr(asset_data, "name", "N/A"),
                )
                continue
            try:
                base_value = Decimal(
                    str(asset_data.to_base)
                )  # 'to_base' is already in user's primary currency
                asset_type = getattr(asset_data, "type_name", "").lower()
                if asset_type in inverted_types_config:
                    total_net_worth -= base_value
                else:
                    total_net_worth += base_value
            except (InvalidOperation, ValueError, TypeError) as e:
                _LOGGER.error(
                    "Error processing to_base for manual asset %s for net worth: %s",
                    getattr(asset_data, "id", "N/A"),
                    e,
                )

        # Sum from Plaid accounts
        for plaid_account_data in plaid_accounts.values():
            plaid_balance = getattr(
                plaid_account_data, "balance", None
            )  # Already a float or None
            plaid_currency = getattr(plaid_account_data, "currency", None)

            if plaid_balance is None or plaid_currency is None:
                _LOGGER.debug(
                    "Plaid Account %s (%s) missing balance or currency, skipping for net worth.",
                    getattr(plaid_account_data, "id", "N/A"),
                    getattr(plaid_account_data, "name", "N/A"),
                )
                continue

            # CRITICAL: Only include Plaid accounts if their currency matches the user's primary currency.
            # Otherwise, we cannot accurately sum them without exchange rates.
            if (
                user_primary_currency
                and plaid_currency.lower() == user_primary_currency
            ):
                try:
                    balance_value = Decimal(
                        str(plaid_balance)
                    )  # Plaid balance is float
                    account_type = getattr(
                        plaid_account_data, "type", ""
                    ).lower()  # Plaid uses 'type'
                    if account_type in inverted_types_config:
                        total_net_worth -= balance_value
                    else:
                        total_net_worth += balance_value
                except (InvalidOperation, ValueError, TypeError) as e:
                    _LOGGER.error(
                        "Error processing balance for Plaid account %s for net worth: %s",
                        getattr(plaid_account_data, "id", "N/A"),
                        e,
                    )
            else:
                _LOGGER.warning(
                    "Plaid Account %s (%s) has currency %s which does not match user's primary currency %s. Excluding from net worth.",
                    getattr(plaid_account_data, "id", "N/A"),
                    getattr(plaid_account_data, "name", "N/A"),
                    plaid_currency,
                    user_primary_currency.upper() if user_primary_currency else "N/A",
                )

        self._attr_native_value = float(total_net_worth)
        self._attr_native_unit_of_measurement = (
            user_primary_currency.upper() if user_primary_currency else None
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available (i.e., coordinator has data)."""
        # Net worth sensor is available as long as the coordinator has run once,
        # even if there are no assets (net worth would be 0).
        # It primarily depends on the 'user' part for currency.
        return (
            super().available
            and self.coordinator.data is not None
            and "user" in self.coordinator.data  # User data is crucial for currency
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return information for the Net Worth device. This device acts as the main integration device."""
        _LOGGER.debug(
            "Device Info for Net Worth Sensor (Main Integration Device): Entry ID %s",
            self._config_entry.entry_id,
        )
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._config_entry.entry_id}_summary")},
            name=NET_WORTH_DEVICE_NAME,
            manufacturer="Lunch Money",
            model="Account Summary Integration",
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_internal_state()
        self.async_write_ha_state()

    @property
    def entity_registry_enabled_default(self) -> bool:
        return True


class LunchMoneyNetWorthCurrencySensor(CoordinatorEntity, SensorEntity):
    """Representation of the Net Worth for a specific currency from Lunch Money assets."""

    _attr_state_class = SensorStateClass.TOTAL
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry: ConfigEntry,
        currency_code: str,
    ) -> None:
        """Initialize the currency-specific Net Worth sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._currency_code = currency_code.upper()
        self._attr_name = f"{NET_WORTH_DEVICE_NAME} Net Worth ({self._currency_code})"
        self._attr_unique_id = f"{self._config_entry.entry_id}_{NET_WORTH_SENSOR_ID_SUFFIX}_{self._currency_code.lower()}"
        self._update_internal_state()

    def _get_manual_asset_data(self) -> dict:
        if self.coordinator.data and "manual_assets" in self.coordinator.data:
            return self.coordinator.data["manual_assets"]
        return {}

    def _get_plaid_account_data(self) -> dict:
        if self.coordinator.data and "plaid_accounts" in self.coordinator.data:
            return self.coordinator.data["plaid_accounts"]
        return {}

    def _update_internal_state(self) -> None:
        """Update the sensor's state, summing from manual and Plaid accounts for this currency."""
        manual_assets = self._get_manual_asset_data()
        plaid_accounts = self._get_plaid_account_data()

        inverted_types_config = self._config_entry.options.get(
            CONF_INVERTED_ASSET_TYPES, DEFAULT_INVERTED_ASSET_TYPES
        )

        currency_net_worth = Decimal("0.0")

        # Sum from manual assets
        for asset_data in manual_assets.values():
            asset_currency = getattr(asset_data, "currency", None)
            if asset_currency and asset_currency.upper() == self._currency_code:
                # For manual assets, 'balance' is the direct balance in its currency.
                # 'to_base' is conversion to primary currency. We want the native currency balance here.
                raw_balance_str = getattr(asset_data, "balance", None)
                parsed_balance = None
                if raw_balance_str is not None:
                    try:
                        parsed_balance = Decimal(str(raw_balance_str))
                    except (InvalidOperation, ValueError, TypeError):
                        _LOGGER.error(
                            "Could not parse balance string '%s' for manual asset %s (currency %s) for currency net worth: %s",
                            raw_balance_str,
                            getattr(asset_data, "id", "N/A"),
                            self._currency_code,
                        )
                        parsed_balance = None  # Ensure it's None on error

                if parsed_balance is not None:
                    asset_type = getattr(asset_data, "type_name", "").lower()
                    if asset_type in inverted_types_config:
                        currency_net_worth -= parsed_balance
                    else:
                        currency_net_worth += parsed_balance

        # Sum from Plaid accounts
        for plaid_account_data in plaid_accounts.values():
            plaid_currency = getattr(plaid_account_data, "currency", None)
            if plaid_currency and plaid_currency.upper() == self._currency_code:
                plaid_balance = getattr(
                    plaid_account_data, "balance", None
                )  # Already a float or None

                if plaid_balance is not None:
                    try:
                        balance_value = Decimal(str(plaid_balance))
                        account_type = getattr(plaid_account_data, "type", "").lower()
                        if account_type in inverted_types_config:
                            currency_net_worth -= balance_value
                        else:
                            currency_net_worth += balance_value
                    except (InvalidOperation, ValueError, TypeError) as e:
                        _LOGGER.error(
                            "Error processing balance for Plaid account %s (currency %s) for currency net worth: %s",
                            getattr(plaid_account_data, "id", "N/A"),
                            self._currency_code,
                            e,
                        )

        self._attr_native_value = float(currency_net_worth)
        self._attr_native_unit_of_measurement = self._currency_code
        self._attr_icon = f"mdi:currency-{self._currency_code.lower()}"  # Dynamic icon based on currency

    @property
    def available(self) -> bool:
        """Return True if entity is available (i.e., coordinator has data)."""
        return super().available and self.coordinator.data is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return information for the Net Worth device. This device acts as the main integration device."""
        _LOGGER.debug(
            "Device Info for Currency Net Worth Sensor (Main Integration Device): Entry ID %s, Currency %s",
            self._config_entry.entry_id,
            self._currency_code,
        )
        return DeviceInfo(
            identifiers={
                (DOMAIN, f"{self._config_entry.entry_id}_summary")
            },  # Link to the main summary device
            name=NET_WORTH_DEVICE_NAME,
            manufacturer="Lunch Money",
            model="Account Summary Integration",
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_internal_state()
        self.async_write_ha_state()

    @property
    def entity_registry_enabled_default(self) -> bool:
        return True
