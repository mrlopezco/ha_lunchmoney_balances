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
    """Set up Lunch Money Balances from a config entry."""
    api_key = entry.data[CONF_API_KEY]
    # Get update_interval from options if available, else from data, else default
    update_interval_minutes = entry.options.get(
        CONF_UPDATE_INTERVAL,
        entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
    )

    lunch_money_api = LunchMoney(access_token=api_key)

    async def async_update_data():
        """Fetch data from Lunch Money API, including assets and user info."""
        try:
            assets_list = await hass.async_add_executor_job(lunch_money_api.get_assets)

            _LOGGER.debug("Fetched Lunch Money assets list: %s", assets_list)

            processed_data = {"assets": {}, "user": None}

            if assets_list and isinstance(assets_list, list):
                _LOGGER.debug("Assets list found with %s items.", len(assets_list))
                valid_assets = [asset for asset in assets_list if hasattr(asset, "id")]

                if not valid_assets:
                    _LOGGER.warning(
                        "The fetched assets list was empty after filtering or did not contain asset objects with an 'id'."
                    )
                else:
                    processed_data["assets"] = {
                        asset.id: asset for asset in valid_assets
                    }
            else:
                _LOGGER.warning(
                    "No assets list found in API response, or the response was not a list. Fetched data: %s",
                    assets_list,
                )

            return processed_data

        except Exception as err:
            _LOGGER.error("Error fetching Lunch Money data: %s", err)
            _LOGGER.exception(
                "Full exception details for error fetching Lunch Money data:"
            )
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Lunch Money Balances Data",  # More generic name for the coordinator
        update_method=async_update_data,
        update_interval=timedelta(minutes=update_interval_minutes),
    )

    # Add listener for options updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

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


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle an options update."""
    await hass.config_entries.async_reload(entry.entry_id)
