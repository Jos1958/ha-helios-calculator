# Home Assistant Helios Calculator
![Helios Calculator](images/HeliosCalculatorBanner.jpeg)

## Intro
The **HELIOS Calculator** is a native Home Assistant Service designed to demonstrate how
Python **SciPy Linear/MILP Programming** can be used from a Home Assistant Custom Component.

**WARNING:** The Current Version is a **Proof of Concept** for the Helios Calculator and does NOT yet deliver a real-life implementation yet.

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-3DDC84?logo=home-assistant&logoColor=#03A9F4)](https://www.home-assistant.io/) 

## Features
- **LP/MILP Optimization:** Uses SciPy linear programming to minimize energy costs for a simple model.
- **WARNING:** This is a Proof of Concept to demonstrate that LINPROG in Home Assistant (actual functions will be delivered later)!

## Description
Provide a service that calculates the lowest cost for a very simple model with 3 input parameters (Energy demand, low tarif and high tarif)
and 3 variables (Low and High Tarif Energy and Solar Production).
<br>See the **[Helios Calculator Documentation](DOC.md)** for details.

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
- See for details: **[Release Notes](RELEASE_NOTES.md)**

# License
**[Helios Calculator License](https://github.com/Jos1958/ha-helios-calculator/blob/main/LICENSE)**

**Keywords:** Solar Panels, Battery, Home Automation, Home Assistant, Optimize your Energy Plan

[README](README.md) - [Doc](DOC.md) - [Why LP](WHY.md) - [Release Notes](RELEASE_NOTES.md) - [License](LICENSE "GitHub Docs")
