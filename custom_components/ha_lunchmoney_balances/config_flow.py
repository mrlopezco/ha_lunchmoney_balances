import logging
from typing import Any

import voluptuous as vol
from requests.exceptions import HTTPError, RequestException

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SelectOptionDict,
    TextSelector,  # Import TextSelector
    TextSelectorConfig,  # Import TextSelectorConfig
)

from awesomeversion import AwesomeVersion
from homeassistant.const import __version__ as HAVERSION
from lunchable import LunchMoney

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    UPDATE_INTERVAL_OPTIONS,
    CONF_INVERTED_ASSET_TYPES,
    DEFAULT_INVERTED_ASSET_TYPES,
    POSSIBLE_ASSET_TYPES,
    CONF_PRIMARY_CURRENCY,  # Import new constant
)

_LOGGER = logging.getLogger(__name__)


async def validate_api_key(hass: HomeAssistant, api_key: str) -> None:
    """Validate the API key by trying to fetch assets."""
    try:
        lunch_money_api = LunchMoney(access_token=api_key)
        await hass.async_add_executor_job(lunch_money_api.get_assets)
    except HTTPError as http_err:
        _LOGGER.error(
            "Lunch Money API HTTP Error during validation: %s (Status: %s)",
            http_err,
            http_err.response.status_code if http_err.response else "N/A",
        )
        raise
    except RequestException as req_err:
        _LOGGER.error(
            "Lunch Money API Request Exception during validation: %s", req_err
        )
        raise ConnectionError(f"Cannot connect to Lunch Money API: {req_err}")
    except Exception as e:
        _LOGGER.exception(
            "Unexpected error during API key validation via lunchable library"
        )
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
            primary_currency = user_input[
                CONF_PRIMARY_CURRENCY
            ].upper()  # Get and normalize currency

            try:
                await validate_api_key(self.hass, api_key)
                await self.async_set_unique_id(api_key)
                self._abort_if_unique_id_configured()

                initial_data = {
                    CONF_API_KEY: api_key,
                    CONF_UPDATE_INTERVAL: update_interval,
                    CONF_PRIMARY_CURRENCY: primary_currency,  # Store primary currency in data
                }

                return self.async_create_entry(
                    title="Lunch Money Balances",
                    data=initial_data,
                    options={
                        CONF_UPDATE_INTERVAL: update_interval,
                        CONF_INVERTED_ASSET_TYPES: DEFAULT_INVERTED_ASSET_TYPES,
                        CONF_PRIMARY_CURRENCY: primary_currency,  # Store primary currency in options
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
                    errors["base"] = "cannot_connect"
            except ConnectionError as conn_err:
                _LOGGER.error(
                    "Could not connect to Lunch Money API during setup: %s", conn_err
                )
                errors["base"] = "cannot_connect"
            except config_entries.OperationNotAllowed:
                return self.async_abort(reason="already_configured")
            except Exception:
                _LOGGER.exception("Unexpected error during authentication test")
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
                vol.Required(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                ): vol.In(UPDATE_INTERVAL_OPTIONS),
                vol.Required(
                    CONF_PRIMARY_CURRENCY,  # Add primary currency field
                    default="USD",  # Default to USD, can be changed by user
                ): TextSelector(
                    TextSelectorConfig(type="text", autocomplete="currency")
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"docs_url": "https://lunchmoney.app/developers"},
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
            # Normalize currency to uppercase before saving
            user_input[CONF_PRIMARY_CURRENCY] = user_input[
                CONF_PRIMARY_CURRENCY
            ].upper()
            return self.async_create_entry(title="", data=user_input)

        current_update_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL,
            self.config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )
        current_inverted_types = self.config_entry.options.get(
            CONF_INVERTED_ASSET_TYPES, DEFAULT_INVERTED_ASSET_TYPES
        )
        current_primary_currency = (
            self.config_entry.options.get(  # Get current primary currency
                CONF_PRIMARY_CURRENCY,
                self.config_entry.data.get(
                    CONF_PRIMARY_CURRENCY, "USD"
                ),  # Default to USD if not set
            )
        )

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=current_update_interval,
                ): vol.In(UPDATE_INTERVAL_OPTIONS),
                vol.Optional(
                    CONF_INVERTED_ASSET_TYPES,
                    default=current_inverted_types,
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(
                                value=atype, label=atype.replace("_", " ").title()
                            )
                            for atype in POSSIBLE_ASSET_TYPES
                        ],
                        multiple=True,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(  # Add primary currency to options flow
                    CONF_PRIMARY_CURRENCY,
                    default=current_primary_currency,
                ): TextSelector(
                    TextSelectorConfig(type="text", autocomplete="currency")
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=options_schema)
