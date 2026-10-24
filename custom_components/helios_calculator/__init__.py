"""Helios Calculator custom component."""
from __future__ import annotations

import logging
import time
import scipy
import voluptuous as vol
import homeassistant.helpers.config_validation as config_validation

from typing import Any
from helios_calculator import _solve_helios_optimization # Import the actual optimizer function

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
        self.last_optimization_result: dict[str, Any] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from coordinator cache."""
        return self.last_optimization_result

# We are NOT using the old YAML-configuratie via configuration.yaml for helios. 
# This solves a warning in hacs.yaml/hassfest.yaml workflow validations
CONFIG_SCHEMA = config_validation.config_entry_only_config_schema(DOMAIN)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Helios Calculator from a config entry."""
    coordinator = HeliosDataUpdateCoordinator(hass)
    
    # Sla de coordinator op in hass.data zodat sensor.py erbij kan
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    async def handle_optimize(call: ServiceCall) -> ServiceResponse:
        """Service handler that calls the SciPy solver and updates coordinator data."""
        demand = call.data["energy_demand_kwh"]
        price_low = call.data["grid_price_low"]
        price_high = call.data["grid_price_high"]

        # Call the Optimizer and (asynch) wait for the result
        optimization_result = await hass.async_add_executor_job(
            _solve_helios_optimization, demand, price_low, price_high
        )

        if not optimization_result.get("success"):
            return {"status": "failed", "details": optimization_result}

        # Save the optimizer result in the coordinator and refresh the coordinator (which triggers the sensor):
        coordinator.last_optimization_result = optimization_result
        await coordinator.async_refresh()

        return optimization_result

    hass.services.async_register(
        DOMAIN,
        "optimize_schedule",
        handle_optimize,
        schema=OPTIMIZE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    # Laad de sensor-platform setup in
    await hass.config_entries.forward_entry_setups(entry, ["sensor"])

    _LOGGER.info("Helios Calculator successfully loaded via Config Entry")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Helios Calculator config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok