"""Test the Radar Fusion config flow."""

from unittest.mock import AsyncMock

import pytest

from homeassistant import config_entries
from homeassistant.components.radar_fusion.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_config_flow(hass: HomeAssistant, mock_setup_entry: AsyncMock) -> None:
    """Test the config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Radar Fusion", "staleness_timeout": 10.0},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Radar Fusion"
    assert result["data"] == {"sensors": []}
    assert len(mock_setup_entry.mock_calls) == 1

    config_entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {"sensors": []}
    assert config_entry.title == "Radar Fusion"


async def test_duplicate_config_entry(hass: HomeAssistant) -> None:
    """Test we can't create duplicate config entries."""
    config_entry = MockConfigEntry(
        data={"sensors": []},
        domain=DOMAIN,
        title="Radar Fusion",
        unique_id=DOMAIN,
    )
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_menu(hass: HomeAssistant) -> None:
    """Test options flow shows menu."""
    config_entry = MockConfigEntry(
        data={"sensors": []},
        domain=DOMAIN,
        title="Radar Fusion",
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"
    assert "sensors" in result["menu_options"]
    assert "zones" in result["menu_options"]
    assert "block_zones" in result["menu_options"]
