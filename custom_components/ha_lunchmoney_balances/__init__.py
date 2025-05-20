import logging
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, CONF_API_KEY, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
from lunchable import LunchMoney
from lunchable.models import PlaidAccountObject  # Import PlaidAccountObject

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
        """Fetch data from Lunch Money API, including assets, Plaid accounts, and user info."""
        try:
            manual_assets_list = await hass.async_add_executor_job(
                lunch_money_api.get_assets
            )
            # Fetch Plaid accounts
            plaid_accounts_list = await hass.async_add_executor_job(
                lunch_money_api.get_plaid_accounts
            )
            user_object = await hass.async_add_executor_job(lunch_money_api.get_user)

            _LOGGER.debug(
                "Fetched Lunch Money manual assets list: %s", manual_assets_list
            )
            _LOGGER.debug(
                "Fetched Lunch Money Plaid accounts list: %s", plaid_accounts_list
            )
            _LOGGER.debug("Fetched Lunch Money user object: %s", user_object)

            processed_data = {"manual_assets": {}, "plaid_accounts": {}, "user": None}

            if user_object:
                processed_data["user"] = user_object

            if manual_assets_list and isinstance(manual_assets_list, list):
                _LOGGER.debug(
                    "Manual assets list found with %s items.", len(manual_assets_list)
                )
                valid_manual_assets = [
                    asset for asset in manual_assets_list if hasattr(asset, "id")
                ]
                if not valid_manual_assets:
                    _LOGGER.warning(
                        "Manual assets list was empty after filtering for 'id'."
                    )
                else:
                    processed_data["manual_assets"] = {
                        asset.id: asset for asset in valid_manual_assets
                    }
            else:
                _LOGGER.warning(
                    "No manual assets list found or response was not a list. Fetched: %s",
                    manual_assets_list,
                )

            # Process Plaid accounts
            if plaid_accounts_list and isinstance(plaid_accounts_list, list):
                _LOGGER.debug(
                    "Plaid accounts list found with %s items.", len(plaid_accounts_list)
                )
                # Ensure each item is a PlaidAccountObject and store by ID
                valid_plaid_accounts = []
                for account in plaid_accounts_list:
                    if isinstance(account, PlaidAccountObject) and hasattr(
                        account, "id"
                    ):
                        valid_plaid_accounts.append(account)
                    else:
                        _LOGGER.warning(
                            "Invalid Plaid account object found: %s", account
                        )

                if not valid_plaid_accounts:
                    _LOGGER.warning(
                        "Plaid accounts list was empty after filtering for valid objects."
                    )
                else:
                    processed_data["plaid_accounts"] = {
                        account.id: account for account in valid_plaid_accounts
                    }
            else:
                _LOGGER.warning(
                    "No Plaid accounts list found or response was not a list. Fetched: %s",
                    plaid_accounts_list,
                )

            _LOGGER.debug(
                "Final processed_data for coordinator: manual_assets keys: %s, plaid_accounts keys: %s, user currency: %s",
                list(processed_data["manual_assets"].keys()),
                list(processed_data["plaid_accounts"].keys()),
                (
                    getattr(processed_data["user"], "currency", "N/A")
                    if processed_data["user"]
                    else "N/A"
                ),
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
        name="Lunch Money Balances Data",
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
