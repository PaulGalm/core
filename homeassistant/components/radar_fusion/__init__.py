"""The Radar Fusion integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_FLOOR_ID,
    CONF_TEST_MODE,
    DOMAIN,
    SERVICE_GET_FLOOR_DATA,
    SERVICE_RESET_HEATMAP,
)
from .coordinator import RadarFusionCoordinator

SERVICE_SET_TEST_MODE = "set_test_mode"

SERVICE_SET_TEST_MODE_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("enabled"): cv.boolean,
    }
)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SWITCH]

SERVICE_GET_FLOOR_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Optional(CONF_FLOOR_ID): vol.Any(cv.string, None),
    }
)

SERVICE_RESET_HEATMAP_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Optional(CONF_FLOOR_ID): vol.Any(cv.string, None),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Radar Fusion from a config entry."""
    # Create coordinator
    coordinator = RadarFusionCoordinator(hass, entry)

    # Store coordinator in runtime_data
    entry.runtime_data = coordinator

    # Store coordinator in hass.data for service access
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

    # Register services
    await async_register_services(hass)

    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Radar Fusion integration (register services globally)."""
    await async_register_services(hass)
    return True


async def async_register_services(hass: HomeAssistant) -> None:
    """Register services for Radar Fusion."""

    async def handle_set_test_mode(call: ServiceCall) -> None:
        """Handle set_test_mode service call."""
        config_entry_id = call.data["config_entry_id"]
        enabled = call.data["enabled"]
        entry = None
        for entry_obj in hass.config_entries.async_entries(DOMAIN):
            if entry_obj.entry_id == config_entry_id:
                entry = entry_obj
                break
        if not entry:
            return
        new_options = dict(entry.options)
        new_options[CONF_TEST_MODE] = enabled
        hass.config_entries.async_update_entry(entry, options=new_options)

    async def handle_get_floor_data(call: ServiceCall) -> dict:
        """Handle get_floor_data service call."""
        config_entry_id = call.data["config_entry_id"]
        floor_id = call.data.get(CONF_FLOOR_ID)

        if config_entry_id not in hass.data[DOMAIN]:
            return {"error": "Config entry not found"}

        coordinator: RadarFusionCoordinator = hass.data[DOMAIN][config_entry_id]
        return coordinator.get_floor_data(floor_id)

    async def handle_reset_heatmap(call: ServiceCall) -> None:
        """Handle reset_heatmap service call."""
        config_entry_id = call.data["config_entry_id"]
        floor_id = call.data.get(CONF_FLOOR_ID)

        if config_entry_id not in hass.data[DOMAIN]:
            return

        coordinator: RadarFusionCoordinator = hass.data[DOMAIN][config_entry_id]
        coordinator.reset_heatmap(floor_id)

    # Only register once
    if not hass.services.has_service(DOMAIN, SERVICE_GET_FLOOR_DATA):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_FLOOR_DATA,
            handle_get_floor_data,
            schema=SERVICE_GET_FLOOR_DATA_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_RESET_HEATMAP):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RESET_HEATMAP,
            handle_reset_heatmap,
            schema=SERVICE_RESET_HEATMAP_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_TEST_MODE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_TEST_MODE,
            handle_set_test_mode,
            schema=SERVICE_SET_TEST_MODE_SCHEMA,
        )
