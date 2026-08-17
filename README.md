# Home Assistant Helios Calculator (ha-helios-calculator)
![Helios Calculator](images/HeliosCalculatorBanner.jpeg)

## Intro
The **HELIOS Calculator** Service is a native Home Assistant custom component designed to calculate mathematically an optimal energy plan.
The Calculator uses **SciPy Linear/MILP Programming** to optimize the Energy Plan 
for **Dynamic** Prices, **Solar** Production, **Battery** Charging/Discharging and **House** Energy Usage.

**WARNING:** The Current Version is a Proof of Concept for the Helios Calculator
The fully functional calculation model will be delivered in version 1.0.0

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-3DDC84?logo=home-assistant&logoColor=#03A9F4)](https://www.home-assistant.io/) 

- **HACS Ready:** Built from the ground up as a native custom component, removing the need for users to configure `pyscript` prerequisites.
- **Performance:** LP solvers require efficient memory and matrix handling, which runs natively and safely within the HA core async loops.
- **Clean API:** Exposes calculated schedules directly as Home Assistant entities/sensors, making it effortless to feed the optimal states into Node-RED or automation scripts.

## Features
- **Simple** configuration (default values for all parameters, runs without changes a test optimization)
- Uses **Linear Programming** to determine the optimal energy plan (highest profit and lowest cost)
- **HACS Ready** native custom component that is built with Python (No need to install PyScript) 
- Fully integrated with **Home Assistant** (no separate engine, uses **SciPy** modules for the LP/MILP)
- **Superfast** and **asynchronous** calculation in HA core loop
- **Open design:** no links with specific (battery or solar) hardware or forecast
- Designed to be able to work together with the **Home Battery Control (HBC)** project
- Calculates for a 1-4 day period
- Start the optimization automatically at the current time (or specify a specific step) for **recalculation** of the plan
- **Clean** and **Simple** input arrays for full day(s) (00:00-24:00)
- Support for 60 and 15 minutes steps
- Future: EV, Heatpump and Boiler devices
- Future: Provide separate module(s) to link to forecast models, battery devices and solar inverters

## Description
Helios calculates an optimized energy plan for a specified horizon (typically 1 to 2 days)
by finding the optimal power setpoints for each interval.
 
The planning horizon is defined by the number of steps and the step duration in minutes.
For example: 24 steps of 60 minutes optimizes a 1-day period.
 
Grid import/export prices and house load forecasts must be provided as input arrays,
containing values for every step in the period.
 
Total Energy Cost is the sum of energy costs per step (calculated from grid import and export power).
The optimizer aims to MINIMIZE the Total Energy Cost over the entire horizon.
Note: Negative costs may occur when exporting energy to the grid or during negative import prices.
 
Note: Without a battery or deferrable loads, optimization opportunities are limited
since a strict power balance between consumption, import, and export must be met in each step.
 
The optimization horizon always starts today (and optionally extends to following days).
By default, the active start step is calculated based on the current time.
Optionally, a specific start step can be defined (e.g., step 1 to start at 00:00).
All input arrays must start at 00:00 today so the optimizer can align prices and forecasts correctly.
 
The resulting Optimized Energy Plan determines the active strategy for the current step
(e.g., NOM, Buy, Sell, Charge, Discharge, Disabled) and provides real-time setpoints
to steer the battery and (TODO) deferrable loads.
 
## Required inputs
- Configuration (steps, step size, start step, solver time/iteration limits, grid limits)
- Grid import prices array (import price per step)
- Grid export prices array (export price per step)
- House consumption forecast (without deferrable loads) array 
 
## Optional inputs
- Solar production forecast array
- Battery parameters
 
## Optional deferrable loads (Future):
- Electric Vehicle (EV) charging profile
- Heat Pump (HP) operation parameters
- Boiler operation parameters

## Installation
- **Prerequisites:**
  - HACS installation on your Home Assistant System
  - For the Helios Dashboard
    - Markdown card  
- **HACS:** 
  * On the HACS Dashboard: Search for "Helios Calculator"
  * Click the "Helios Calculator" to open the Helios README page with the <Download> button
  * Press the "Download" button to download the Helios Calculator (in /config/custom_components/helios_calculator)

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

- **Automation:**
  * todo

- **Dashboard:**
  * todo   

## What's New:
?? **[Release Notes](RELEASE_NOTES.md)**
-- **Proof of Concept**:

## Documentation
?? **[Helios Calculator Documentation](DOC.md)**

## Advanced

## Updating

## Credits

## Contributing
At the moment it is not advised to develop additional features based on the current version.
The current code is not very stable yet so your changes may not work on the next release.
Only small bug fixes will be accepted.
Please raise an issue to report a bug or to request for new functionality.

# License

# Help

**Keywords:** Solar Panels, Battery, Home Automation, Home Assistant, Optimize your Energy Plan