# ha-helios-calculator
![Helios Calculator](images/HeliosCalculatorBanner.jpeg)

**H**ome **E**nergy **L**inear **I**ntegrated **O**ptimization **S**ervice 

##Intro
The HELIOS Calculator Service is a Python function to calculate an Optimized Energy Plan                            
The Calculator uses SciPy Linear/MILP Programming to optimize the Energy Plan 
for Solar Production, Battery Charging/Discharging and expected House Energy Usage 
for Dynamic Prices.

* WARNING: The Current Version is a Proof of Concept for the Helios Calculator
* The actual calculation model will be delivered in version 1.0.0

##Description
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
 
##Required inputs
- Configuration (steps, step size, start step, solver time/iteration limits, grid limits)
- Grid import prices array (import price per step)
- Grid export prices array (export price per step)
- House consumption forecast array
 
##Optional inputs
- Solar production forecast array
- Battery parameters
 
##Optional deferrable loads (Future):
- Electric Vehicle (EV) charging profile
- Heat Pump (HP) operation parameters
- Boiler operation parameters

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-3DDC84?logo=home-assistant&logoColor=#03A9F4)](https://www.home-assistant.io/) 

## Features
- Simple configuration (default values for all parameters)
- Uses Linear Programming to determine the optimal energy plan (highest profit and lowest cost)
- Superfast and asynchronous calculation
- Fully integrated with Home Assistant (no separate engine, uses Python and SciPy modules for the LP/MILP)
- Open design: no links with specific (battery or solar) hardware or forecast
- Calculates for 1, 2 or 3 day period
- Support for hour and 15 minutes steps
- Future: EV, Heatpump and Boiler devices
- Future: Provide separate module(s) to link to forecast models, battery devices and solar inverters

## Installation
- **HACS:** 
  * You need to installation HACS on your Home Assistant System
  * Select the HACS Dashboard
  * Search for "Helios Calculator"
  * Click the "Helios Calculator" to open the readme page with the <download> button
  * Press the "Download" button to download the calculator to /config/custom_components/helios_calculator
- **Integration:**
  * Settings -> Devices and Services - [Integrations]
  * Press the <+ Add Integration>-button
  * Search for "Helios Calculator"
  * Click the "Helios Calculator"
  * A Popup appears for the Helios Calculator
  * Press the <Send>-button to add the integration 
  * A popup appears: "Configuration created for Helios Calculator"
  * Press <Complete>-button
  * Note: All further configuration is done in the call to Helios Calculator Service  
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