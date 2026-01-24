"""Config flow for the Radar Fusion integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BLOCK_ZONES,
    CONF_FLOOR_ID,
    CONF_POSITION_X,
    CONF_POSITION_Y,
    CONF_ROTATION,
    CONF_SENSORS,
    CONF_STALENESS_TIMEOUT,
    CONF_TARGET_ENTITIES,
    CONF_VERTICES,
    CONF_ZONES,
    DEFAULT_NAME,
    DEFAULT_STALENESS_TIMEOUT,
    DOMAIN,
    parse_vertices,
)


class RadarFusionConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Radar Fusion."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        # Only allow one config entry for this integration
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME),
                data={CONF_SENSORS: []},
                options={
                    CONF_ZONES: [],
                    CONF_BLOCK_ZONES: [],
                    CONF_STALENESS_TIMEOUT: user_input.get(
                        CONF_STALENESS_TIMEOUT, DEFAULT_STALENESS_TIMEOUT
                    ),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Optional(
                        CONF_STALENESS_TIMEOUT, default=DEFAULT_STALENESS_TIMEOUT
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=300, unit_of_measurement="seconds"
                        )
                    ),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> RadarFusionOptionsFlow:
        """Get the options flow for this handler."""
        return RadarFusionOptionsFlow()


class RadarFusionOptionsFlow(OptionsFlow):
    """Handle options flow for Radar Fusion."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._sensors: list[dict[str, Any]] = []
        self._zones: list[dict[str, Any]] = []
        self._block_zones: list[dict[str, Any]] = []
        self._edit_index: int | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["sensors", "zones", "block_zones", "settings"],
        )

    # Sensor management
    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage sensors."""
        self._sensors = self.config_entry.data.get(CONF_SENSORS, []).copy()
        return self.async_show_menu(
            step_id="sensors",
            menu_options=["add_sensor", "edit_sensor", "remove_sensor"],
        )

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a new sensor."""
        errors = {}

        if user_input is not None:
            try:
                # Validate target entities - should be 6 (3 targets × 2 coordinates)
                target_entities = user_input[CONF_TARGET_ENTITIES]
                if len(target_entities) != 6:
                    errors["base"] = "invalid_target_count"
                else:
                    sensor_config = {
                        CONF_FLOOR_ID: user_input.get(CONF_FLOOR_ID),
                        CONF_POSITION_X: user_input[CONF_POSITION_X],
                        CONF_POSITION_Y: user_input[CONF_POSITION_Y],
                        CONF_ROTATION: user_input.get(CONF_ROTATION, 0),
                        CONF_TARGET_ENTITIES: target_entities,
                    }
                    self._sensors.append(sensor_config)

                    # Update config entry data
                    new_data = {**self.config_entry.data, CONF_SENSORS: self._sensors}
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    return await self.async_step_sensors()
            except (ValueError, KeyError):
                errors["base"] = "invalid_input"

        return self.async_show_form(
            step_id="add_sensor",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_FLOOR_ID): selector.FloorSelector(),
                    vol.Required(CONF_POSITION_X, default=0): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=-10000, max=10000, unit_of_measurement="mm"
                        )
                    ),
                    vol.Required(CONF_POSITION_Y, default=0): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=-10000, max=10000, unit_of_measurement="mm"
                        )
                    ),
                    vol.Optional(CONF_ROTATION, default=0): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=359, unit_of_measurement="degrees"
                        )
                    ),
                    vol.Required(CONF_TARGET_ENTITIES): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor",
                            multiple=True,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_remove_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove a sensor."""
        self._sensors = self.config_entry.data.get(CONF_SENSORS, []).copy()

        if not self._sensors:
            return await self.async_step_sensors()

        if user_input is not None:
            sensor_index = int(user_input["sensor_index"])
            if 0 <= sensor_index < len(self._sensors):
                self._sensors.pop(sensor_index)
                new_data = {**self.config_entry.data, CONF_SENSORS: self._sensors}
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )
            return await self.async_step_sensors()

        sensor_options = [
            f"{i}: Floor {s.get(CONF_FLOOR_ID, 'None')} - "
            f"Position ({s.get(CONF_POSITION_X)}, {s.get(CONF_POSITION_Y)})"
            for i, s in enumerate(self._sensors)
        ]

        return self.async_show_form(
            step_id="remove_sensor",
            data_schema=vol.Schema(
                {
                    vol.Required("sensor_index"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=sensor_options)
                    ),
                }
            ),
        )

    # Zone management
    async def async_step_zones(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage zones."""
        self._zones = self.config_entry.data.get(CONF_ZONES, []).copy()
        return self.async_show_menu(
            step_id="zones",
            menu_options=["add_zone", "remove_zone"],
        )

    async def async_step_add_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a new zone."""
        errors = {}

        if user_input is not None:
            try:
                # Parse and validate vertices
                vertices = parse_vertices(user_input[CONF_VERTICES])
                if len(vertices) < 3:
                    errors["base"] = "insufficient_vertices"
                else:
                    zone_name = user_input[CONF_NAME]
                    floor_id = user_input.get(CONF_FLOOR_ID)

                    # Check uniqueness on floor
                    existing_names = [
                        z[CONF_NAME]
                        for z in self._zones
                        if z.get(CONF_FLOOR_ID) == floor_id
                    ]
                    if zone_name in existing_names:
                        errors["base"] = "duplicate_zone_name"
                    else:
                        zone_config = {
                            CONF_NAME: zone_name,
                            CONF_FLOOR_ID: floor_id,
                            CONF_VERTICES: vertices,
                        }
                        self._zones.append(zone_config)

                        # Update options
                        return self.async_create_entry(
                            data={**self.config_entry.data, CONF_ZONES: self._zones}
                        )
            except ValueError:
                errors["base"] = "invalid_vertices"

        return self.async_show_form(
            step_id="add_zone",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Optional(CONF_FLOOR_ID): selector.FloorSelector(),
                    vol.Required(CONF_VERTICES): selector.TextSelector(
                        selector.TextSelectorConfig(multiline=True)
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "vertices_example": "[[0,0], [1000,0], [1000,1000], [0,1000]]"
            },
        )

    async def async_step_remove_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove a zone."""
        self._zones = self.config_entry.data.get(CONF_ZONES, []).copy()

        if not self._zones:
            return await self.async_step_zones()

        if user_input is not None:
            zone_index = int(user_input["zone_index"])
            if 0 <= zone_index < len(self._zones):
                self._zones.pop(zone_index)
                return self.async_create_entry(
                    data={**self.config_entry.data, CONF_ZONES: self._zones}
                )

        zone_options = [
            f"{i}: {z.get(CONF_NAME)} (Floor: {z.get(CONF_FLOOR_ID, 'None')})"
            for i, z in enumerate(self._zones)
        ]

        return self.async_show_form(
            step_id="remove_zone",
            data_schema=vol.Schema(
                {
                    vol.Required("zone_index"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=zone_options)
                    ),
                }
            ),
        )

    # Block zone management
    async def async_step_block_zones(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage block zones."""
        self._block_zones = self.config_entry.data.get(CONF_BLOCK_ZONES, []).copy()
        return self.async_show_menu(
            step_id="block_zones",
            menu_options=["add_block_zone", "remove_block_zone"],
        )

    async def async_step_add_block_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a new block zone."""
        errors = {}

        if user_input is not None:
            try:
                vertices = parse_vertices(user_input[CONF_VERTICES])
                if len(vertices) < 3:
                    errors["base"] = "insufficient_vertices"
                else:
                    zone_name = user_input[CONF_NAME]
                    floor_id = user_input.get(CONF_FLOOR_ID)

                    # Check uniqueness on floor
                    existing_names = [
                        z[CONF_NAME]
                        for z in self._block_zones
                        if z.get(CONF_FLOOR_ID) == floor_id
                    ]
                    if zone_name in existing_names:
                        errors["base"] = "duplicate_zone_name"
                    else:
                        block_zone_config = {
                            CONF_NAME: zone_name,
                            CONF_FLOOR_ID: floor_id,
                            CONF_VERTICES: vertices,
                        }
                        self._block_zones.append(block_zone_config)

                        return self.async_create_entry(
                            data={
                                **self.config_entry.data,
                                CONF_BLOCK_ZONES: self._block_zones,
                            }
                        )
            except ValueError:
                errors["base"] = "invalid_vertices"

        return self.async_show_form(
            step_id="add_block_zone",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Optional(CONF_FLOOR_ID): selector.FloorSelector(),
                    vol.Required(CONF_VERTICES): selector.TextSelector(
                        selector.TextSelectorConfig(multiline=True)
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "vertices_example": "[[100,100], [200,100], [200,200], [100,200]]"
            },
        )

    async def async_step_remove_block_zone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove a block zone."""
        self._block_zones = self.config_entry.data.get(CONF_BLOCK_ZONES, []).copy()

        if not self._block_zones:
            return await self.async_step_block_zones()

        if user_input is not None:
            zone_index = int(user_input["zone_index"])
            if 0 <= zone_index < len(self._block_zones):
                self._block_zones.pop(zone_index)
                return self.async_create_entry(
                    data={**self.config_entry.data, CONF_BLOCK_ZONES: self._block_zones}
                )

        zone_options = [
            f"{i}: {z.get(CONF_NAME)} (Floor: {z.get(CONF_FLOOR_ID, 'None')})"
            for i, z in enumerate(self._block_zones)
        ]

        return self.async_show_form(
            step_id="remove_block_zone",
            data_schema=vol.Schema(
                {
                    vol.Required("zone_index"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=zone_options)
                    ),
                }
            ),
        )

    # Settings
    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage settings."""
        if user_input is not None:
            return self.async_create_entry(
                data={**self.config_entry.data, **user_input}
            )

        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_STALENESS_TIMEOUT,
                        default=self.config_entry.data.get(
                            CONF_STALENESS_TIMEOUT, DEFAULT_STALENESS_TIMEOUT
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=300, unit_of_measurement="seconds"
                        )
                    ),
                }
            ),
        )
