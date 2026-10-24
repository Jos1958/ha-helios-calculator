"""Helios Calculator Custom Component for Optimize Energy Cost."""
from __future__ import annotations

import logging
#import time
import voluptuous as vol
import homeassistant.helpers.config_validation as config_validation

from typing import Any
from .helios_calculator import solve_optimize_energy_cost # Import the actual optimizer function from the current folder (helios_calculator.py)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

DOMAIN = "helios_calculator"
_LOGGER = logging.getLogger(__name__)

OPTIMIZE_SCHEMA = vol.Schema({
    vol.Required("energy_demand_kwh"): vol.Coerce(float),
    vol.Optional("grid_price_low", default=0.15): vol.Coerce(float),
    vol.Optional("grid_price_high", default=0.35): vol.Coerce(float),
})


class HeliosDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching of Helios Calculator Data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
        self.last_optimization_result: dict[str, Any] = {} # Initialize the Coordinator with an empty dictionary

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from coordinator cache for the Helios Calculator Sensor."""
        return self.last_optimization_result

# We are NOT using the old YAML-configuratie via configuration.yaml for helios. 
# This solves a warning in hacs.yaml/hassfest.yaml workflow validations
CONFIG_SCHEMA = config_validation.config_entry_only_config_schema(DOMAIN)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Helios Calculator from a config entry."""
    coordinator = HeliosDataUpdateCoordinator(hass)
    
    # Save the coordinator in hass.data for the DOMAIN, this allows access by sensor.py
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    async def handle_optimize_energy_cost(call: ServiceCall) -> ServiceResponse:
        """Service handler that calls the SciPy solver and updates coordinator data."""
        demand = call.data["energy_demand_kwh"]
        price_low = call.data["grid_price_low"]
        price_high = call.data["grid_price_high"]

        # Call the Optimizer and (asynch) wait for the result
        start_time = dt_util.now().isoformat() # Home Assistant Local Time
        optimization_result = await hass.async_add_executor_job(
            solve_optimize_energy_cost, start_time, demand, price_low, price_high # See helios_calculator.py
        )

        if not optimization_result.get("success"):
            return {"status": "failed", "details": optimization_result}

        # Save the optimizer result in the coordinator and refresh the coordinator (which triggers the helios sensor to update):
        coordinator.last_optimization_result = optimization_result
        await coordinator.async_refresh()

        return optimization_result

    hass.services.async_register(
        DOMAIN,
        "optimize_energy_cost",
        handle_optimize_energy_cost, # Call the above function (which calls helios_calculator_optimize_energy_cost in helios_calculator.py)
        schema=OPTIMIZE_SCHEMA, # See services.yaml
        supports_response=SupportsResponse.ONLY,
    )

    # Load the sensor-platform setup (see sensor.py for the Helios Calculator sensor(s))
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    _LOGGER.info("Helios Calculator successfully loaded via Config Entry")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Helios Calculator config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok