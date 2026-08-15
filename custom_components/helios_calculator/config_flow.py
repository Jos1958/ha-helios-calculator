"""Config flow for Helios Calculator integration."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

DOMAIN = "helios_calculator"


class HeliosCalculatorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Helios Calculator."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step when added via the UI."""
        # Prevent configuring the same integration multiple times
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="Helios Calculator",
                data={},
            )

        # Display a simple setup form with a submit button
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
        )