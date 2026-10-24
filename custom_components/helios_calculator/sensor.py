"""Sensor platform for Helios Calculator."""
from __future__ import annotations

from typing import Any
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL  
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, HeliosDataUpdateCoordinator # from __init__.py

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up Helios sensor based on a config entry."""
    coordinator: HeliosDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HeliosCalculatorOptimalCostSensor(coordinator)]) # Initialize the Sensor Class and pass the Coordinator
    return True

class HeliosCalculatorOptimalCostSensor(CoordinatorEntity[HeliosDataUpdateCoordinator], SensorEntity):
    """Representation of the Helios Calculator Optimal Cost Sensor with status and attributes."""

    _attr_has_entity_name = True
    _attr_name = "Helios Calculator Optimal Cost"
    _attr_unique_id = "helios_calculator_optimal_cost"
    _attr_native_unit_of_measurement = "EUR"
    _attr_icon = "mdi:shield-sun-outline"

    _unrecorded_attributes = frozenset({MATCH_ALL}) # Do not sent attributes to the HA recorder
    
    def __init__(self, coordinator: HeliosDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator) # Keep the coordinator to later (when needed) retrieve the data for the Helios Calculator Sensor
        self.entity_id = "sensor.helios_calculator_optimal_cost"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor (total cost in EUR)."""
        if self.coordinator.data:
            return self.coordinator.data.get("total_cost_eur") # State value for the sensor is total cost in euro
        return None # No coordinator data available (state is None)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the calculated details as attributes."""
        if not self.coordinator.data:
            return {"Error": "Coordinator Data for Helios Sensor does not exist!"} # No coordinator data available (no attributes available)
        
        return { # Attributes of the Sensor are retrieved from the Coordinator data
            "last_calculated": self.coordinator.data.get("start_time"),
            "scipy_version": self.coordinator.data.get("scipy"),
            "execution_time_ms": self.coordinator.data.get("execution_time_ms"),
            "input_parameters": self.coordinator.data.get("input_parameters"),
            "variables": self.coordinator.data.get("variables"),
        }