"""Helios Calculator custom component."""
from __future__ import annotations # must be at the top!

import logging
import time
from typing import Any

from scipy.optimize import linprog
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.util import dt as dt_util

DOMAIN = "helios_calculator"
OUTPUT_ENTITY = "optimal_cost"
_LOGGER = logging.getLogger(__name__)

# Validation schema for the service input
OPTIMIZE_SCHEMA = vol.Schema({
    vol.Required("energy_demand_kwh"): vol.Coerce(float),
    vol.Optional("grid_price_low", default=0.15): vol.Coerce(float),
    vol.Optional("grid_price_high", default=0.35): vol.Coerce(float),
})

def _solve_helios_optimization(
    demand: float, price_low: float, price_high: float
) -> dict[str, Any]:
    """Synchronous, CPU-intensive function that executes SciPy HiGHS.
    
    This runs outside the asyncio event-loop in a separate thread.
    """
    t_start = time.perf_counter() # Start of LP run
    start_time = dt_util.now().isoformat()
    _LOGGER.debug("SciPy HiGHS optimalization has started using a background-thread")

    # Example: Minimeze the energy costs c * x
    # x0 = kWh for cheap power from grid, x1 = kWh is expensive power from grid, x2 = kWh from solar panels
    c = [price_low, price_high, 0.05]  # Cost per kWh per source

    # Limitation: x0 + x1 + x2 >= demand (or -x0 - x1 - x2 <= -demand)
    A_ub = [[-1.0, -1.0, -1.0]]
    b_ub = [-demand]

    # Bounds: Minimum 0 kWh, maximum 10 kWh for cheap electricity tariff and 8 kWh solar
    bounds = [(0, 10), (0, None), (0, 8)]

    # Perform the HiGHS-solver using Lineair Programming (LP) of SciPy
    result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")

    t_end = time.perf_counter() # End of LP run
    execution_time = (t_end - t_start) * 1000 # calculate execution time in milliseconds

    if not result.success:
        _LOGGER.error("HiGHS solver failed: %s", result.message)
        return {"success": False, "error": result.message}

    return {
        "success": True,
        "execution_time_ms": round(execution_time, 2),
        "start_time": start_time,
        "total_cost_eur": round(float(result.fun), 2),
        "kwh_low_tariff": round(float(result.x[0]), 2),
        "kwh_high_tariff": round(float(result.x[1]), 2),
        "kwh_solar": round(float(result.x[2]), 2),
    }


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set-up of the Helios Calculator component (Proof of Concept only)."""

    async def handle_optimize(call: ServiceCall) -> ServiceResponse:
        """Service handler that calls the SciPy solver."""
        demand = call.data["energy_demand_kwh"]
        price_low = call.data["grid_price_low"]
        price_high = call.data["grid_price_high"]

        # The "heavy" CPU task for the SciPy solver is moved to the executor threadpool
        optimization_result = await hass.async_add_executor_job(
            _solve_helios_optimization, demand, price_low, price_high
        )

        if not optimization_result.get("success"):
            return {"status": "failed", "details": optimization_result}

        last_calc_dt = dt_util.now().isoformat() # Get the current timestamp
        
        # Update the state and attributes in Home Assistant (cost plus details)
        hass.states.async_set(
            f"{DOMAIN}.{OUTPUT_ENTITY}",
            optimization_result["total_cost_eur"],
            attributes={
                "unit_of_measurement": "€",
                "unique_id": f"{DOMAIN}_{OUTPUT_ENTITY}",
                "friendly_name": "Helios Optimale Kosten",
                "last_calculated": last_calc_dt,
                "details": optimization_result,
            },
        )

        return optimization_result

    # Register the service
    hass.services.async_register(
        DOMAIN,
        "optimize_schedule",
        handle_optimize,
        schema=OPTIMIZE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    return True
    
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Helios Calculator from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Register services, setup platforms, or load initial logic here
    _LOGGER.info("Helios Calculator successfully loaded via Config Entry")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Helios Calculator config entry."""
    _LOGGER.info("Helios Calculator unloaded")
    return True    