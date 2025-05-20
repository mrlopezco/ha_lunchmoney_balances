# Lunch Money Balance Integration for Home Assistant

[![Validate with HACS](https://github.com/mrlopezco/ha_lunchmoney_balances/actions/workflows/validate.yaml/badge.svg)](https://github.com/mrlopezco/ha_lunchmoney_balances/actions/workflows/validate.yaml)
[![GitHub Release][releases-shield]][releases]
[![GitHub Code Size][code-size-shield]][code-size]
[![License][license-shield]][license]
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)


Home Assistant custom integration to fetch and display your asset balances from [Lunch Money](https://lunchmoney.app/).

**This integration is currently under development. Use at your own risk.**

## Features

*   Fetches manually managed asset balances from your Lunch Money account.
*   Creates a Home Assistant sensor for each asset, displaying its current balance and currency.
*   Configurable update frequency: "Twice a day (every 12 hours)" or "Daily (every 24 hours)".
*   Securely stores your Lunch Money API key using Home Assistant's configuration flow.
*   Handles API errors and provides logging.
*   Option to reconfigure the update interval after initial setup.

## Prerequisites

*   Home Assistant version 2023.1.0 or newer.
*   HACS (Home Assistant Community Store) installed.
*   A Lunch Money account with an active API Key. You can generate an API key from your Lunch Money account under "Settings" -> "Developers".

## Installation

### Via HACS (Recommended)

1.  **Ensure HACS is installed.** If not, follow the [HACS installation guide](https://hacs.xyz/docs/setup/download).
2.  **Add as a custom repository (until officially in HACS default):**
    *   Open HACS in Home Assistant (usually in the sidebar).
    *   Go to "Integrations".
    *   Click the three dots in the top-right corner and select "Custom repositories".
    *   Enter `https://github.com/mrlopezco/ha_lunchmoney_balances` in the "Repository" field.
    *   Select "Integration" in the "Category" dropdown.
    *   Click "ADD".
3.  **Install the "Lunch Money Balance" integration:**
    *   Search for "Lunch Money Balance" in HACS Integrations.
    *   Click "INSTALL" or "DOWNLOAD".
    *   Follow the prompts to complete the installation.
4.  **Restart Home Assistant:** This is crucial for the integration to be loaded.

### Manual Installation (Advanced)

1.  Download the latest release `.zip` file from the [Releases page](https://github.com/mrlopezco/ha_lunchmoney_balances/releases).
2.  Extract the `ha_lunchmoney_balances` folder from the zip.
3.  Copy the `ha_lunchmoney_balances` folder into your Home Assistant `custom_components` directory. If the `custom_components` directory doesn't exist, create it.
    *   The final path should look like: `<config_directory>/custom_components/ha_lunchmoney_balances/`.
4.  Restart Home Assistant.

## Configuration

After restarting Home Assistant:

1.  Go to **Settings > Devices & Services**.
2.  Click the **+ ADD INTEGRATION** button in the bottom right.
3.  Search for "Lunch Money Balance" and select it.
4.  **Enter your Lunch Money API Key**.
5.  Select your desired **Update Frequency** from the dropdown.
6.  Click **SUBMIT**.

The integration will connect to Lunch Money, fetch your assets, and create sensor entities.

### Reconfiguring Update Interval

You can change the update interval after the initial setup:

1.  Go to **Settings > Devices & Services**.
2.  Find the "Lunch Money Balance" integration card.
3.  Click on **CONFIGURE** (or the options/pencil icon).
4.  Select the new desired **Update Frequency**.
5.  Click **SUBMIT**.

## Sensors

For each asset in your Lunch Money account, a sensor will be created in Home Assistant.

*   **Entity ID Format**: `sensor.lunch_money_[asset_display_name_or_name]` (spaces in name replaced by underscores, all lowercase).
*   **State**: The current balance of the asset.
*   **Unit of Measurement**: The currency of the asset (e.g., USD, CAD, EUR).

**Key Attributes for each sensor:**

*   `asset_id` (int): Unique identifier for the asset in Lunch Money.
*   `type_name` (str): Primary type of the asset (e.g., `cash`, `credit`, `investment`).
*   `subtype_name` (str, optional): Asset subtype (e.g., `retirement`, `checking`).
*   `institution_name` (str, optional): Name of the institution holding the asset.
*   `display_name` (str, optional): The display name of the asset from Lunch Money.
*   `asset_original_name` (str): The original `name` field of the asset from Lunch Money.
*   `balance_as_of` (datetime string): ISO 8601 timestamp of when the balance was last reported by Lunch Money.
*   `to_base_currency` (float, optional): The balance converted to your Lunch Money primary currency, if applicable.
*   `attribution` (str): "Data provided by Lunch Money".

## Troubleshooting

*   **"Invalid authentication" error during setup:**
    *   Verify your Lunch Money API key is correct and has not expired.
    *   Ensure there are no leading/trailing spaces.
*   **"Cannot connect" error during setup:**
    *   Check Home Assistant's internet connectivity.
    *   Ensure Lunch Money API (`https://dev.lunchmoney.app`) is accessible from your Home Assistant instance.
*   **Sensors not appearing or updating:**
    *   Check the Home Assistant logs for errors related to `ha_lunchmoney_balances` or `lunchable`. Go to **Settings > System > Logs**.
    *   Ensure the `lunchable` library was installed correctly.
    *   Verify the assets you expect to see are not "excluded from balance sheet" or similar settings in Lunch Money if those affect API visibility.
*   **"No assets found or assets attribute missing in API response" in logs:**
    *   This means the API call was successful, but no assets were returned or the response format was unexpected. Check your Lunch Money account to ensure you have assets.
    *   The `lunchable` library might need an update if Lunch Money changed its API response structure.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on the [GitHub repository](https://github.com/mrlopezco/ha_lunchmoney_balances).

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes.
4.  Ensure your code passes linting and tests (if applicable).
5.  Submit a pull request with a clear description of your changes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*This integration uses the [lunchable](https://github.com/juftin/lunchable) Python library to interact with the Lunch Money API.*

[releases-shield]: https://img.shields.io/github/v/release/mrlopezco/ha_lunchmoney_balances.svg?style=for-the-badge&include_prereleases
[releases]: https://github.com/mrlopezco/ha_lunchmoney_balances/releases
[code-size-shield]: https://img.shields.io/github/languages/code_size/mrlopezco/ha_lunchmoney_balances.svg?style=for-the-badge
[code-size]: https://github.com/mrlopezco/ha_lunchmoney_balances
[license-shield]: https://img.shields.io/github/license/mrlopezco/ha_lunchmoney_balances.svg?style=for-the-badge
[license]: https://github.com/mrlopezco/ha_lunchmoney_balances/blob/main/LICENSE