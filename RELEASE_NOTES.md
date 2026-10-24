# Release Notes

## 0.8.4 (2026-10-24) Updates after Review
- Added a Sensor to the Custom Component with the resulting optimal cost state and attributes
- Documentation updates/alignment

## 0.8.x (2026-08-15) Custom Component and HACS support (Proof of Concept)
- Proof of concept for a version that runs as a Home Assistant Custom Component (simple model but using LP) (__init__.py)
- Brand files in sub folder of the custom component (with icon.png and logo.png)
- Call the SciPy Linear Programming function with the HiGHS solver
- Update Home Assistant Entity in the custom component
- Import several libraries including linprog (scipy.optimize)
- Home Assistant Manifest file (manifest.json) for custom component with version number and scipy dependency 
- Home Assistant Setup file (config_flow.py) to allow installation/configuration of the integration (otherwise component needs to be added to configuration.yaml)
- Home Assistant Service file (service.yaml), required for the interface of the service helios_calculator.optimize_schedule) 
- Home Assistant strings.json (with additional text for the config flow) and translations/n/r/nl.json with dutch translations)
- Created a README.md (directly linked by HACS) and a RELEASE_NOTES.md (v0.1.0-v0.8.0), created an empty DOC.md file
- Created the GitHub GNUv3 License file (automatically filled when type of license selected)
- Simple Installation flow for the integration (config_flow.py)
- Investigated and Implemented the HACS requirements for a custom component that is available in the HACS repository: 
  - Note: The custom component could already be added to my HA installation via the custom repository option in HACS
  - Created the hacs.json with the custom component, render_readme: true, home assistant min release version 
  - Added the document link and the github issue link to the manifest.json
  - Added two workflows: .github/workflow/hacs.yaml & hassfest.yaml, checked results under actions (corrected errors)
  - Created a release in github (v0.8.0) with the same number as used in the manifest.json
  - Forked from hacs/default (hacs repository), created a separate branch, updated the file integration. with "Jos1958/ha-helios-calculator" (alphabetic order)
  - Commit the change (in integration.) to a new branch
  - Create Pull Request and Fill the related checklist (links to release, hacs and hassfest workflow results) for the pull request (Do not the: Merge Pull Request)
    Make sure the Pull Request is done to the hacs/default (and not to my own master)! Resubmitted the request on 2026-08-17

## 0.1.0 (2026-05-19)
- Initial commit with the first implementation of a LP call in pyscript
- The functionality is started from an HA automation
- Errors in the compilation or runtime can be found in the Home Assistant System Log

[README](README.md) - [Doc](DOC.md) - [Why LP](WHY.md) - **Release Notes** - [License](LICENSE "GitHub Docs")
