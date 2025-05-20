"""Sensor platform for Lunch Money Balance integration."""

import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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

    # Check if coordinator.data is available and not None
    if coordinator.data is None:
        _LOGGER.error(
            "No data received from coordinator during sensor setup. Skipping entity creation."
        )
        return

    entities = []
    for asset_id, asset_data in coordinator.data.items():
        if asset_data:  # Ensure asset_data is not None
            entities.append(
                LunchMoneyBalanceSensor(coordinator, asset_id, config_entry.entry_id)
            )
        else:
            _LOGGER.warning(
                "Asset data for ID %s is missing, skipping sensor creation.", asset_id
            )

    async_add_entities(
        entities, True
    )  # Second argument True enables an immediate update of added entities


class LunchMoneyBalanceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Lunch Money asset balance sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.MONETARY  # Using MONETARY device class
    _attr_attribution = ATTRIBUTION

    def __init__(
        self, coordinator: DataUpdateCoordinator, asset_id: int, entry_id: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._asset_id = asset_id
        self._entry_id = entry_id  # Store entry_id for unique_id generation
        # Initial data fetch handled by CoordinatorEntity
        self._update_internal_data()  # Initialize internal data based on current coordinator data

    def _update_internal_data(self) -> None:
        """Safely update internal asset data from coordinator."""
        self._asset_data = (
            self.coordinator.data.get(self._asset_id) if self.coordinator.data else None
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self._asset_data is not None

    @property
    def name(self) -> str | None:
        """Return the name of the sensor."""
        if self._asset_data:
            # Use display_name if available, otherwise fall back to name
            asset_name = getattr(self._asset_data, "display_name", None) or getattr(
                self._asset_data, "name", "Unknown Asset"
            )
            return f"Lunch Money {asset_name}"
        return None  # Should not happen if available is True

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this sensor."""
        # Using entry_id in unique_id ensures it's unique even if multiple accounts are set up (though current flow doesn't support it)
        return f"{self._entry_id}_{self._asset_id}"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor (the balance)."""
        if self._asset_data and hasattr(self._asset_data, "balance"):
            try:
                return float(self._asset_data.balance)
            except (ValueError, TypeError):
                _LOGGER.error(
                    "Could not parse balance '%s' for asset %s",
                    self._asset_data.balance,
                    self._asset_id,
                )
                return None
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        if (
            self._asset_data
            and hasattr(self._asset_data, "currency")
            and self._asset_data.currency
        ):
            return self._asset_data.currency.upper()
        return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the state attributes."""
        if not self._asset_data:
            return None

        attrs = {
            ATTR_ASSET_ID: self._asset_id,
        }

        # Helper to add attribute if present in asset_data
        def add_attr_if_present(attr_key, data_key):
            if (
                hasattr(self._asset_data, data_key)
                and getattr(self._asset_data, data_key) is not None
            ):
                attrs[attr_key] = getattr(self._asset_data, data_key)

        add_attr_if_present(ATTR_TYPE_NAME, "type_name")
        add_attr_if_present(ATTR_SUBTYPE_NAME, "subtype_name")
        add_attr_if_present(ATTR_INSTITUTION_NAME, "institution_name")
        add_attr_if_present(
            ATTR_DISPLAY_NAME, "display_name"
        )  # Adding display_name also to attributes
        add_attr_if_present(ATTR_TO_BASE_CURRENCY, "to_base")  # API uses 'to_base'

        if (
            hasattr(self._asset_data, "balance_as_of")
            and self._asset_data.balance_as_of
        ):
            try:
                # Ensure balance_as_of is a valid ISO 8601 string before parsing
                parsed_date = datetime.fromisoformat(
                    self._asset_data.balance_as_of.replace("Z", "+00:00")
                )
                attrs[ATTR_BALANCE_AS_OF] = parsed_date.isoformat()
            except ValueError:
                _LOGGER.warning(
                    "Could not parse balance_as_of date: %s",
                    self._asset_data.balance_as_of,
                )
                attrs[ATTR_BALANCE_AS_OF] = (
                    self._asset_data.balance_as_of
                )  # Store as is if parsing fails

        # Add original name if display_name was used for the entity name
        if hasattr(self._asset_data, "name") and getattr(
            self._asset_data, "display_name", None
        ):
            attrs["asset_original_name"] = self._asset_data.name

        return attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_internal_data()  # Update internal data
        if self._asset_id not in (self.coordinator.data or {}):
            _LOGGER.info(
                "Asset ID %s (Sensor: %s) no longer found in Lunch Money data. It might have been deleted. Entity will become unavailable.",
                self._asset_id,
                self.entity_id,
            )
            # The entity will become unavailable due to the `available` property check
        self.async_write_ha_state()

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when firstadded to the entity registry."""
        return True  # Entities are enabled by default
