import logging
from typing import Any

import voluptuous as vol
from requests.exceptions import HTTPError, RequestException

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import (
    async_get_clientsession,
)  # Import for API calls

from awesomeversion import AwesomeVersion
from homeassistant.const import __version__ as HAVERSION
from lunchable import LunchMoney

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    UPDATE_INTERVAL_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)


async def validate_api_key(hass: Any, api_key: str) -> None:
    """Validate the API key by trying to fetch assets."""
    try:
        lunch_money_api = LunchMoney(access_token=api_key)
        # Use hass.async_add_executor_job for blocking I/O calls
        await hass.async_add_executor_job(lunch_money_api.get_assets)
    except HTTPError as http_err:
        _LOGGER.error(
            "Lunch Money API HTTP Error during validation: %s (Status: %s)",
            http_err,
            http_err.response.status_code if http_err.response else "N/A",
        )
        # Re-raise HTTPError to be specifically handled by the caller
        raise
    except (
        RequestException
    ) as req_err:  # Catch other requests-related errors (connection, timeout)
        _LOGGER.error(
            "Lunch Money API Request Exception during validation: %s", req_err
        )
        raise ConnectionError(f"Cannot connect to Lunch Money API: {req_err}")
    except Exception as e:  # Catch any other unexpected error during the API call
        _LOGGER.exception(
            "Unexpected error during API key validation via lunchable library"
        )
        # Raise a ConnectionError to map to "cannot_connect" or a generic error in the flow
        raise ConnectionError(
            f"Unexpected error communicating with Lunch Money API: {e}"
        )


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
                # If validate_api_key doesn't raise, proceed
                await self.async_set_unique_id(api_key)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Lunch Money Balances",  # Updated title to match domain if desired
                    data={
                        CONF_API_KEY: api_key,
                        CONF_UPDATE_INTERVAL: update_interval,
                    },
                )
            except HTTPError as http_err:
                if (
                    http_err.response is not None
                    and http_err.response.status_code == 401
                ):
                    _LOGGER.error("Invalid Lunch Money API key (HTTP 401).")
                    errors["base"] = "invalid_auth"
                else:
                    _LOGGER.error(
                        "Lunch Money API returned an HTTP error: %s", http_err
                    )
                    errors["base"] = "cannot_connect"  # Or a more specific "api_error"
            except (
                ConnectionError
            ) as conn_err:  # Raised by validate_api_key for network or unexpected issues
                _LOGGER.error(
                    "Could not connect to Lunch Money API during setup: %s", conn_err
                )
                errors["base"] = "cannot_connect"
            except (
                config_entries.OperationNotAllowed
            ):  # For _abort_if_unique_id_configured
                return self.async_abort(reason="already_configured")
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during authentication test")
                errors["base"] = "unknown"

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
            # Logic to update config_entry and return
            self.hass.config_entries.async_update_entry(
                self.config_entry, data={**self.config_entry.data, **user_input}
            )
            return self.async_create_entry(title="", data={})

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
