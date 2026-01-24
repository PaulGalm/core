"""Test the Radar Fusion integration."""

from homeassistant.components.radar_fusion.const import DOMAIN
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_setup_and_remove_config_entry(
    hass: HomeAssistant,
) -> None:
    """Test setting up and removing a config entry."""
    # Setup the config entry with no sensors/zones
    config_entry = MockConfigEntry(
        data={"sensors": []},
        domain=DOMAIN,
        title="Radar Fusion",
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check the integration is loaded
    assert config_entry.state.name == "LOADED"

    # Check coordinator is stored in runtime_data
    assert config_entry.runtime_data is not None

    # Check service is registered
    assert hass.services.has_service(DOMAIN, "get_floor_data")

    # Remove the config entry
    assert await hass.config_entries.async_remove(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check the integration is unloaded
    assert config_entry.state.name == "NOT_LOADED"
