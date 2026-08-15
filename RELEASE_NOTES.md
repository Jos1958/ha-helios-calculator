# Release Notes

## 0.8.0 (Under development)
- Proof of concept for a version that runs as a Home Assistant Custom Component (simple model but using LP)
- Investigate HACS requirements, what is needed to deploy the Custom Component via HACS
- Call the SciPy Linear Programming function with the HiGHS solver
- Update Home Assistant Entity in the custom component
- Import several libraries including linprog (scipy.optimize)
- Manifest file for Home Assistant with scipy dependency and config_flow
- Simple Service (service.yaml) 
- Simple Installation flow for the integration (config_flow.py)
- Logo and Icon png files

## 0.7.0 (Not published yet)
- Improved Home Assistant Mockup that allows the code to be developed and tested in Visual Studio
- Added additional comment in the code and replaced all dutch comments by english
- Protect agains infeasible solution with invalid SoC Start (outside SoC Min and Max)
- Protect against infeasible solution with unreachable SoC Min End for remaining steps and max charge power
- Extended validation of input parameters and extra output arrays and parameters
- Extended error handling for exceptions (Try/Except, Traceback, Initialize all payload variables)
- Validate Costs (total cost = sum of step costs) and return as calc_result 
- Generate 92 Test Scenarios with an expected result for regression testing
- Write the run results to an (csv) export file in Visual Studio with a summary of the input and outputs 

## 0.6.0 (2026-08-01)
- Added Solar Mode, solar production optimization (Solar modes: enabled, modulating/dimming, binary, disabled)
- Split the code into a Helios Calculator (HA Service) and Helios Module (Actual Solver) for testing in Visual Studio
- Note: Helios Module contains most of the earlier history and Helios Calculator now contains new code
- Warning: pyscript runs the Helios Calculator and includes the Helios Module from the modules folder (in VS: both are in the same folder)

## 0.5.0 (2026-06-28)
- Extended the payload and the related output entity for presentation on a Home Assistant Dashboard
- Created HBC lab page with plan results (status, graph, table) using apexchart and markdown cards
- Helios Calculator Banner

## 0.4.0 (2026-06-24)
- Input parameters now include a dictionary for the Battery Configuration
- Return payload to the Home Assistant automation
- Use current time as starting step when start_step is 0 (e.g. at 15:23 start at 15:00 with step 16)
- Calculate a battery strategy from the optimization results (concept version)

## 0.3.0 (2026-06-23)
- Added Input arrays (prices, house and solar forecast) as parameters to the calculation/optimization service
- Home Assistant Automation calls the service with these parameters

## 0.2.0 (2026-05-20)
- Introduced the Energy Balance Rule 

## 0.1.1 (2026-05-19)
- **Features:** 
  * No changes

- **Fixes:**
  * Renamed the py file to lower case with underscore

- **Documentation:**
  * Added a RELEASE_NOTES_md

- **Files Changed:**
  - `pyscript/helios_calculator.py` (was HeliosCalculator.py)

## 0.1.0 (2026-05-19)
- Initial commit with the first implementation of a LP call in pyscript
- The functionality is started from an HA automation
- Errors in the compilation or runtime can be found in the Home Assistant System Log
