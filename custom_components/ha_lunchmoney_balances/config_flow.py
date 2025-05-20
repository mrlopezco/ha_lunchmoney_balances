import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import (
    async_get_clientsession,
)  # Import for API calls
from lunchable import LunchMoney
from lunchable.models import LunchMoneyAPIError  # More specific import for API Error

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    UPDATE_INTERVAL_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)


async def validate_api_key(hass: Any, api_key: str) -> bool:
    """Validate the API key by trying to fetch assets."""
    try:
        lunch_money_api = LunchMoney(access_token=api_key)
        # The library might make a synchronous call, wrap it
        await hass.async_add_executor_job(lunch_money_api.get_assets)
        return True
    except LunchMoneyAPIError as e:
        _LOGGER.error("Lunch Money API Error during validation: %s", e)
        raise  # Re-raise to be caught in the flow
    except Exception as e:  # Catch any other unexpected errors during validation
        _LOGGER.error("Unexpected error during API key validation: %s", e)
        raise ConnectionError("Cannot connect to Lunch Money API")


class LunchMoneyBalanceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Lunch Money Balance integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            update_interval = user_input[CONF_UPDATE_INTERVAL]

            try:
                await validate_api_key(self.hass, api_key)
            except LunchMoneyAPIError:
                errors["base"] = "invalid_auth"
                _LOGGER.error("Invalid Lunch Money API key provided.")
            except ConnectionError:
                errors["base"] = "cannot_connect"
                _LOGGER.error("Could not connect to Lunch Money API during setup.")
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during authentication test")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    api_key
                )  # Set unique_id to prevent duplicate entries for the same API key
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Lunch Money Balance",  # You can make this more dynamic, e.g., user's Lunch Money name if available
                    data={
                        CONF_API_KEY: api_key,
                        CONF_UPDATE_INTERVAL: update_interval,
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Required(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                ): vol.In(UPDATE_INTERVAL_OPTIONS),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "docs_url": "https://lunchmoney.app/developers"
            },  # Example placeholder
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return LunchMoneyBalanceOptionsFlowHandler(config_entry)


class LunchMoneyBalanceOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a change to the Lunch Money Balance options."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Combine new options with existing data, then create new entry with updated data
            # This effectively updates the config entry's options.
            updated_data = {**self.config_entry.data, **user_input}
            # Home Assistant will automatically update the entry if the title matches.
            # For options, it's often better to just update the options directly.
            # However, the original prompt implied storing interval in entry.data.
            # If it should be in options, the approach is slightly different.
            # For this case, we're creating a new entry to replace the old one,
            # which is a common pattern if data is changing.
            # A more direct options update would be:
            # return self.async_create_entry(title="", data=user_input)
            # which merges user_input into config_entry.options
            # For now, sticking to the user's pattern of storing in data.
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=updated_data
            )
            return self.async_create_entry(title="", data={})  # Signal success

        # Get current values for defaults
        current_api_key = self.config_entry.data.get(
            CONF_API_KEY
        )  # Should not be changed here, but good to have if needed
        current_update_interval = self.config_entry.data.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=current_update_interval,
                ): vol.In(UPDATE_INTERVAL_OPTIONS),
            }
        )
        return self.async_show_form(step_id="init", data_schema=options_schema)
