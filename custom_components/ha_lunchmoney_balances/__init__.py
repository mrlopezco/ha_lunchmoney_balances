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
            assets = await hass.async_add_executor_job(lunch_money_api.get_assets)
            _LOGGER.debug("Fetched Lunch Money assets: %s", assets)
            if assets and hasattr(assets, "assets"):
                return {
                    asset.id: asset for asset in assets.assets
                }  # Store assets by their ID for easy lookup
            _LOGGER.warning(
                "No assets found or assets attribute missing in API response."
            )
            return {}
        except Exception as err:
            _LOGGER.error("Error fetching Lunch Money assets: %s", err)
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
