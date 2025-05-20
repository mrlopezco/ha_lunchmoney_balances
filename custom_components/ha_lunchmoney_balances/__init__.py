import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_API_KEY, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
from lunchable import LunchMoney

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lunch Money Balance from a config entry."""
    api_key = entry.data[CONF_API_KEY]
    update_interval_minutes = entry.data.get(
        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
    )

    lunch_money_api = LunchMoney(access_token=api_key)

    async def async_update_data():
        """Fetch data from Lunch Money API."""
        try:
            # Use hass.async_add_executor_job for blocking I/O calls
            # Based on the logs, lunch_money_api.get_assets() directly returns a list of AssetsObject
            fetched_assets_list = await hass.async_add_executor_job(
                lunch_money_api.get_assets
            )

            _LOGGER.debug("Fetched Lunch Money assets list: %s", fetched_assets_list)

            if fetched_assets_list and isinstance(fetched_assets_list, list):
                _LOGGER.debug(
                    "Assets list found with %s items.", len(fetched_assets_list)
                )
                # Filter out assets that might be considered inactive or closed, if desired
                # For now, we'll include all assets returned by the API that have an 'id'
                valid_assets = [
                    asset for asset in fetched_assets_list if hasattr(asset, "id")
                ]

                if not valid_assets:
                    _LOGGER.warning(
                        "The fetched assets list was empty after filtering or did not contain asset objects with an 'id'."
                    )
                    return {}

                return {
                    asset.id: asset for asset in valid_assets
                }  # Store assets by their ID for easy lookup

            _LOGGER.warning(
                "No assets list found in API response, or the response was not a list. Fetched data: %s",
                fetched_assets_list,
            )
            return (
                {}
            )  # Return empty dict if no assets or issues with the response structure
        except Exception as err:
            _LOGGER.error("Error fetching Lunch Money assets: %s", err)
            _LOGGER.exception(
                "Full exception details for error fetching Lunch Money assets:"
            )
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Lunch Money Balance",
        update_method=async_update_data,
        update_interval=timedelta(minutes=update_interval_minutes),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
