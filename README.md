# Lunch Money Balance Integration for Home Assistant

[![Validate with HACS](https://github.com/mrlopezco/ha_lunchmoney_balances/actions/workflows/validate.yaml/badge.svg)](https://github.com/mrlopezco/ha_lunchmoney_balances/actions/workflows/validate.yaml)
[![GitHub Release][releases-shield]][releases]
[![GitHub Code Size][code-size-shield]][code-size]
[![License][license-shield]][license]
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

This Home Assistant custom integration allows you to fetch and display your asset balances from [Lunch Money](https://lunchmoney.app/).

**This integration is currently under development. Use at your own risk.**

## Features

* Fetches manually managed asset balances from your Lunch Money account.

* Creates a Home Assistant sensor for each asset, showing its current balance and currency.

* Offers configurable update frequencies: "Twice a day (every 12 hours)" or "Daily (every 24 hours)".

* Securely stores your Lunch Money API key using Home Assistant's configuration flow.

* Includes error handling for API issues and provides logging.

* Allows reconfiguring the update interval after initial setup.

* Calculates and displays your total net worth in your primary currency.

* Provides currency-specific net worth sensors for all currencies found in your assets.

## Prerequisites

* Home Assistant version 2023.1.0 or newer.

* HACS (Home Assistant Community Store) installed.

* A Lunch Money account with an active API Key. You can generate an API key from your Lunch Money account under "Settings" -> "Developers".

## Installation

### Via HACS (Recommended)

1. **Ensure HACS is installed.** If not, follow the [HACS installation guide](https://hacs.xyz/docs/setup/download).

2. **Add as a custom repository (until officially in HACS default):**

   * Open HACS in Home Assistant (usually in the sidebar).

   * Go to "Integrations".

   * Click the three dots in the top-right corner and select "Custom repositories".

   * Enter `https://github.com/mrlopezco/ha_lunchmoney_balances` in the "Repository" field.

   * Select "Integration" in the "Category" dropdown.

   * Click "ADD".

3. **Install the "Lunch Money Balance" integration:**

   * Search for "Lunch Money Balance" in HACS Integrations.

   * Click "INSTALL" or "DOWNLOAD".

   * Follow the prompts to complete the installation.

4. **Restart Home Assistant:** This is crucial for the integration to be loaded.

### Manual Installation (Advanced)

1. Download the latest release `.zip` file from the [Releases page](https://github.com/mrlopezco/ha_lunchmoney_balances/releases).

2. Extract the `ha_lunchmoney_balances` folder from the zip.

3. Copy the `ha_lunchmoney_balances` folder into your Home Assistant `custom_components` directory. If the `custom_components` directory doesn't exist, create it.

   * The final path should look like: `<config_directory>/custom_components/ha_lunchmoney_balances/`.

4. Restart Home Assistant.

## Configuration

After restarting Home Assistant, you will configure the integration through the Home Assistant UI.

1. Go to **Settings > Devices & Services**.

2. Click the **+ ADD INTEGRATION** button in the bottom right.

3. Search for "Lunch Money Balance" and select it.

4. You will be prompted to enter the following:

   * **Lunch Money API Key**: Enter your personal API key obtained from Lunch Money settings.

   * **Update Frequency**: Select how often the integration should fetch updates from Lunch Money (e.g., "Twice a day (every 12 hours)" or "Daily (every 24 hours)").

   * **Primary Currency**: Enter your primary currency (e.g., "USD", "CAD", "EUR"). This currency will be used for the main Net Worth sensor.

5. Click **SUBMIT**.

The integration will then connect to Lunch Money, fetch your assets, and create sensor entities in Home Assistant.

### Reconfiguring Update Interval and Inverted Asset Types

You can change the update interval and configure which asset types should have their balances inverted (e.g., credit cards and loans) after the initial setup.

1. Go to **Settings > Devices & Services**.

2. Find the "Lunch Money Balance" integration card.

3. Click on **CONFIGURE** (or the options/pencil icon).

4. You can adjust:

   * **Update Frequency**: Select a new desired update interval.

   * **Inverted Asset Types**: Choose which asset types (e.g., `credit`, `loan`) should have their balances displayed as negative values. By default, 'credit' and 'loan' are inverted.

   * **Primary Currency**: Update your primary currency if needed.

5. Click **SUBMIT**.

## Sensors

For each asset in your Lunch Money account, a sensor will be created in Home Assistant. There are also dedicated sensors for your overall net worth.

* **Individual Asset/Account Sensor Entity ID Format**: `sensor.lunch_money_[asset_display_name_or_name]` (spaces in name replaced by underscores, all lowercase).

  * **State**: The current balance of the asset.

  * **Unit of Measurement**: The currency of the asset (e.g., USD, CAD, EUR).

  * **Key Attributes for each sensor:**

    * `asset_id` (int): Unique identifier for the asset in Lunch Money.

    * `item_source` (str): Indicates if the asset is `manual` or `plaid`.

    * `asset_type_name` (str, for manual assets): Primary type of the asset (e.g., `cash`, `credit`, `investment`).

    * `plaid_account_type` (str, for Plaid accounts): Primary type of the Plaid account (e.g., `depository`, `credit card`).

    * `subtype_name` (str, optional, for manual assets): Asset subtype (e.g., `retirement`, `checking`).

    * `plaid_account_subtype` (str, optional, for Plaid accounts): Plaid account subtype.

    * `institution_name` (str, optional): Name of the institution holding the asset.

    * `display_name` (str, optional, for manual assets): The display name of the asset from Lunch Money.

    * `plaid_account_name` (str, for Plaid accounts): The name of the Plaid account.

    * `asset_original_name` (str, for manual assets, if different from display name): The original `name` field of the asset from Lunch Money.

    * `balance_as_of` (datetime string): ISO 8601 timestamp of when the balance was last reported by Lunch Money.

    * `to_base_currency_value` (float, for manual assets, optional): The balance converted to your Lunch Money primary currency, if applicable.

    * `balance_inverted` (bool): Indicates if the balance has been inverted based on the `CONF_INVERTED_ASSET_TYPES` configuration.

    * `currency_code` (str): The currency code of the sensor's balance.

    * `plaid_mask` (str, for Plaid accounts): The last few digits of the account number.

    * `plaid_status` (str, for Plaid accounts): The status of the Plaid account.

    * `attribution` (str): "Data provided by Lunch Money".

* **Overall Net Worth Sensor**: This sensor provides your total net worth.

  * **Entity ID Format**: `sensor.lunch_money_summary_net_worth`.

  * **State**: Your aggregated net worth value.

  * **Unit of Measurement**: Your configured primary currency.

  * **Device Name**: `Lunch Money Summary`.

* **Currency-Specific Net Worth Sensors**: For each unique currency found across your manual assets and Plaid accounts, a separate net worth sensor will be created.

  * **Entity ID Format**: `sensor.lunch_money_summary_net_worth_[currency_code_lowercase]`.

  * **State**: The aggregated balance of all assets in that specific currency.

  * **Unit of Measurement**: The specific currency code (e.g., "CAD", "EUR").

  * **Device Name**: `Lunch Money Summary`.

## Troubleshooting

* **"Invalid authentication" error during setup:**

  * Verify your Lunch Money API key is correct and has not expired.

  * Ensure there are no leading/trailing spaces.

* **"Cannot connect" error during setup:**

  * Check Home Assistant's internet connectivity.

  * Ensure Lunch Money API (`https://dev.lunchmoney.app`) is accessible from your Home Assistant instance.

* **Sensors not appearing or updating:**

  * Check the Home Assistant logs for errors related to `ha_lunchmoney_balances` or `lunchable`. Go to **Settings > System > Logs**.

  * Ensure the `lunchable` library was installed correctly.

  * Verify the assets you expect to see are not "excluded from balance sheet" or similar settings in Lunch Money if those affect API visibility.

* **"No assets found or assets attribute missing in API response" in logs:**

  * This means the API call was successful, but no assets were returned or the response format was unexpected. Check your Lunch Money account to ensure you have assets.

  * The `lunchable` library might need an update if Lunch Money changed its API response structure.

* **Net Worth or Currency Net Worth Sensor not showing the expected value:**

  * Ensure the `CONF_PRIMARY_CURRENCY` is set correctly in the integration's options, as this is used for the main net worth calculation.

  * Plaid accounts are only included in the main net worth calculation if their currency matches your configured primary currency.

  * Review the `CONF_INVERTED_ASSET_TYPES` settings in the integration's options to ensure assets like credit cards and loans are being correctly added or subtracted from your net worth.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on the [GitHub repository](https://github.com/mrlopezco/ha_lunchmoney_balances).

1. Fork the repository.

2. Create a new branch for your feature or bug fix.

3. Make your changes.

4. Ensure your code passes linting and tests (if applicable).

5. Submit a pull request with a clear description of your changes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

*This integration uses the [lunchable](https://github.com/juftin/lunchable) Python library to interact with the Lunch Money API*

[releases-shield]: https://img.shields.io/github/v/release/mrlopezco/ha_lunchmoney_balances.svg?style=for-the-badge&include_prereleases
[releases]: https://github.com/mrlopezco/ha_lunchmoney_balances/releases
[code-size-shield]: https://img.shields.io/github/languages/code_size/mrlopezco/ha_lunchmoney_balances.svg?style=for-the-badge
[code-size]: https://github.com/mrlopezco/ha_lunchmoney_balances
[license-shield]: https://img.shields.io/github/license/mrlopezco/ha_lunchmoney_balances.svg?style=for-the-badge
[license]: https://github.com/mrlopezco/ha_lunchmoney_balances/blob/main/LICENSE