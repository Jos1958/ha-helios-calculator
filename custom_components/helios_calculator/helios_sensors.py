"""Sensor platform for Helios Calculator."""
from __future__ import annotations

from typing import Any
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
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
    async_add_entities([HeliosOptimalCostSensor(coordinator)])
    return True

class HeliosOptimalCostSensor(CoordinatorEntity[HeliosDataUpdateCoordinator], SensorEntity):
    """Representation of the Helios Optimal Cost Sensor with status and attributes."""

    _attr_has_entity_name = True
    _attr_name = "Optimale Kosten"
    _attr_unique_id = "helios_optimal_cost"
    _attr_native_unit_of_measurement = "EUR"
    _attr_icon = "mdi:solar-power"

    def __init__(self, coordinator: HeliosDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor (total cost in EUR)."""
        if self.coordinator.data:
            return self.coordinator.data.get("total_cost_eur")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the calculated details as attributes."""
        if not self.coordinator.data:
            return {}
        
        return {
            "last_calculated": self.coordinator.data.get("start_time"),
            "scipy_version": self.coordinator.data.get("scipy"),
            "execution_time_ms": self.coordinator.data.get("execution_time_ms"),
            "kwh_low_tariff": self.coordinator.data.get("kwh_low_tariff"),
            "kwh_high_tariff": self.coordinator.data.get("kwh_high_tariff"),
            "kwh_solar": self.coordinator.data.get("kwh_solar"),
        }