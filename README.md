# Home Assistant Helios Calculator (ha-helios-calculator)
![Helios Calculator](images/HeliosCalculatorBanner.jpeg)

## Intro
The **HELIOS Calculator** Service is a native Home Assistant custom component designed to calculate mathematically an optimal energy plan.
The Calculator uses **SciPy Linear/MILP Programming** to optimize the Energy Plan. 

**WARNING:** The Current Version is a **Proof of Concept** for the Helios Calculator and does NOT yet deliver a real-life implementation.

The fully functional calculation model will be delivered in version 1.0.0.

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-3DDC84?logo=home-assistant&logoColor=#03A9F4)](https://www.home-assistant.io/) 

## Features
- **LP/MILP Optimization:** Uses SciPy linear programming to maximize profit and minimize energy costs.
- **WARNING: This is the Proof of Concept to demonstrate that LINPROG in Home Assistant (actual functions will be delivered later)

## Future Functions
- **Dynamic** Prices, **Solar** Production, **Battery** Charging/Discharging and **House** Energy Usage.
- **Native HA Integration:** Pure Python custom component (HACS-ready), runs without PyScript or external engines.
- **Asynchronous & Fast:** Lightweight execution built directly into the HA core asynchronous loop.
- **Zero-Config Setup:** Out-of-the-box defaults let you run a test optimization immediately without configuration.
- **Independent:** Open design compatible with any dynamic price, solar, battery, or forecast brand/provider.
- **Flexible Horizon & Intervals:** Calculates energy plan for one or more day(s) with 15-minute or 60-minute time steps.
- **Dynamic Recalculation:** Runs automatically from the current timestamp or from a user-defined step.
- **HBC Ready:** Designed for seamless integration with the HBC Marstek Battery Interface
- **Clean Data Structure:** Simple full-day input and output arrays (00:00-24:00).
- **Device Support:** EV, Heat Pump, and Boiler integration (deferrable devices).
- **Modular Connectors:** Dedicated modules for energy providers, solar forecasts, battery integrations and solar inverter integrations.
- **HBC Integration:** Integrate as an additional Strategy with the Home Battery Control (HBC) project.

## Description


## Installation
- **Prerequisites:**
  - HACS installation on your Home Assistant System
    
- **HACS:** 
  * On the HACS Dashboard: **Search** for "Helios Calculator"
  * Click the **"Helios Calculator"** to open the Helios README page with the <Download> button
  * Press the **"Download"** button to download the Helios Calculator (to /config/custom_components/helios_calculator)
  * **Herstart** Home Assistant

- **Integration:**
  * Open the Integration Page (**Settings** -> **Devices and Services** - **[Integrations]**)
  * Press the **+ Add Integration** button
  * Search for "Helios Calculator"
  * Click the "Helios Calculator"
  * A Popup appears for the Helios Calculator with a "Send" button
  * Press **Send** to add the integration 
  * A popup appears: "Configuration created for Helios Calculator" with a "Complete" button
  * Press **Complete** to close the popup
  * **Note:** All further configuration is done in the call to Helios Calculator Service  

## What's New:
- **Proof of Concept**: for LINPROG in a HA Custom Component
**[Release Notes](RELEASE_NOTES.md)**

## Documentation
**[Helios Calculator Documentation](DOC.md)**

## Contributing
At the moment it is not advised to develop additional features based on the current version.
The current code is not very stable yet so your changes may not work on the next release.
Only small bug fixes will be accepted.
Please raise an issue to report a bug or to request for new functionality.

# License
**[Helios Optimizer License](https://github.com/Jos1958/ha-helios-optimizer/blob/main/LICENSE)**

**Keywords:** Solar Panels, Battery, Home Automation, Home Assistant, Optimize your Energy Plan

[README](README.md) - [Doc](DOC.md) - [Why LP](WHY.md) - [Release Notes](RELEASE_NOTES.md) - [License](LICENSE "GitHub Docs")
