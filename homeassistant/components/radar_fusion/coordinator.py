"""Coordinator for Radar Fusion integration."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_state_change_event,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

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
    DEFAULT_STALENESS_TIMEOUT,
    DOMAIN,
    point_in_polygon,
    transform_coordinates,
)

_LOGGER = logging.getLogger(__name__)


class RadarFusionCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage radar fusion data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=1),
            config_entry=config_entry,
        )

        self.sensors: list[dict[str, Any]] = config_entry.data.get(CONF_SENSORS, [])
        self.zones: list[dict[str, Any]] = config_entry.options.get(CONF_ZONES, [])
        self.block_zones: list[dict[str, Any]] = config_entry.options.get(
            CONF_BLOCK_ZONES, []
        )
        self.staleness_timeout: int = config_entry.options.get(
            CONF_STALENESS_TIMEOUT, DEFAULT_STALENESS_TIMEOUT
        )

        # Track raw sensor states and timestamps
        self._sensor_states: dict[str, Any] = {}
        self._last_updates: dict[str, datetime] = {}

        # Track block zone states (entity_id -> is_on)
        self._block_zone_states: dict[str, bool] = {}

        # Store all entity IDs to track
        self._tracked_entities: set[str] = set()
        for sensor in self.sensors:
            self._tracked_entities.update(sensor.get(CONF_TARGET_ENTITIES, []))

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data."""
        now = datetime.now()

        # Get current sensor states
        for entity_id in self._tracked_entities:
            state = self.hass.states.get(entity_id)
            if state and state.state not in ("unknown", "unavailable"):
                self._sensor_states[entity_id] = state.state
                self._last_updates[entity_id] = now

        # Process targets from all sensors
        all_targets = self._process_all_targets(now)

        # Filter by block zones and staleness
        filtered_targets = self._filter_targets(all_targets)

        # Group targets by floor
        targets_by_floor: dict[str | None, list[dict[str, Any]]] = {}
        for target in filtered_targets:
            floor_id = target["floor_id"]
            if floor_id not in targets_by_floor:
                targets_by_floor[floor_id] = []
            targets_by_floor[floor_id].append(target)

        return {
            "targets_by_floor": targets_by_floor,
            "all_targets": all_targets,
            "filtered_targets": filtered_targets,
            "sensor_count": len(self.sensors),
            "zone_count": len(self.zones),
            "block_zone_count": len(self.block_zones),
        }

    def _process_all_targets(self, now: datetime) -> list[dict[str, Any]]:
        """Process all targets from all sensors."""
        all_targets = []

        for sensor_config in self.sensors:
            floor_id = sensor_config.get(CONF_FLOOR_ID)
            sensor_x = sensor_config.get(CONF_POSITION_X, 0)
            sensor_y = sensor_config.get(CONF_POSITION_Y, 0)
            rotation = sensor_config.get(CONF_ROTATION, 0)
            target_entities = sensor_config.get(CONF_TARGET_ENTITIES, [])

            # Group entities by target (target1_x, target1_y, target2_x, etc.)
            targets_data: dict[int, dict[str, Any]] = {}

            for entity_id in target_entities:
                # Parse entity to determine target number and coordinate
                # Expected formats:
                # - sensor.ld2450_target1_x
                # - sensor.test_radar_1_target_1_x (with underscores)
                parts = entity_id.split("_")
                if len(parts) < 2:
                    continue

                # Find target number and coordinate
                target_num = None
                coord_type = None
                for i, part in enumerate(parts):
                    # Look for "target" followed by a number (with or without underscore)
                    if part == "target" and i + 1 < len(parts):
                        # Next part should be the number
                        try:
                            target_num = int(parts[i + 1])
                        except ValueError:
                            continue
                    elif part.startswith("target"):
                        # target1, target2, etc. (no underscore)
                        try:
                            target_num = int(part[6:])
                        except ValueError:
                            continue
                    elif part in ("x", "y") and i == len(parts) - 1:
                        coord_type = part

                if target_num is None or coord_type is None:
                    continue

                # Get state value
                if entity_id not in self._sensor_states:
                    continue

                try:
                    value = float(self._sensor_states[entity_id])
                except (ValueError, TypeError):
                    continue

                # Store in targets_data
                if target_num not in targets_data:
                    targets_data[target_num] = {
                        "target_num": target_num,
                        "sensor_config": sensor_config,
                    }
                targets_data[target_num][coord_type] = value

                # Track last update
                if entity_id in self._last_updates:
                    if "last_update" not in targets_data[target_num]:
                        targets_data[target_num]["last_update"] = self._last_updates[
                            entity_id
                        ]
                    else:
                        # Use most recent update
                        targets_data[target_num]["last_update"] = max(
                            targets_data[target_num]["last_update"],
                            self._last_updates[entity_id],
                        )

            # Transform and add complete targets
            for target_data in targets_data.values():
                if "x" not in target_data or "y" not in target_data:
                    continue

                # Transform coordinates
                global_x, global_y = transform_coordinates(
                    target_data["x"],
                    target_data["y"],
                    sensor_x,
                    sensor_y,
                    rotation,
                )

                all_targets.append(
                    {
                        "sensor_id": id(sensor_config),
                        "target_num": target_data["target_num"],
                        "floor_id": floor_id,
                        "local_x": target_data["x"],
                        "local_y": target_data["y"],
                        "x": global_x,
                        "y": global_y,
                        "last_update": target_data.get("last_update", now),
                        "age_seconds": (
                            now - target_data.get("last_update", now)
                        ).total_seconds(),
                        "sensor_entities": target_entities,
                    }
                )

        return all_targets

    def _filter_targets(self, targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter targets by staleness and block zones."""
        filtered = []

        for target in targets:
            # Filter stale targets
            if target["age_seconds"] > self.staleness_timeout:
                continue

            # Check if target is in any active block zone
            in_block_zone = False
            floor_id = target["floor_id"]

            for block_zone in self.block_zones:
                # Only check block zones on same floor
                if block_zone.get(CONF_FLOOR_ID) != floor_id:
                    continue

                # Check if block zone is enabled
                block_zone_entity_id = f"switch.{DOMAIN}_{block_zone.get('name', '').lower().replace(' ', '_')}_block"
                if not self._block_zone_states.get(block_zone_entity_id, False):
                    continue

                # Check if target is inside block zone
                vertices = block_zone.get(CONF_VERTICES, [])
                if point_in_polygon(target["x"], target["y"], vertices):
                    in_block_zone = True
                    break

            if not in_block_zone:
                filtered.append(target)

        return filtered

    @callback
    def update_block_zone_state(self, entity_id: str, is_on: bool) -> None:
        """Update block zone state."""
        self._block_zone_states[entity_id] = is_on
        # Trigger immediate update
        self.async_set_updated_data(self.data or {})

        # Subscribe to state changes
        @callback
        def _async_state_changed(event: Event[EventStateChangedData]) -> None:
            """Handle state changes."""
            new_state = event.data["new_state"]
            if new_state is None:
                return

            entity_id = event.data["entity_id"]

            # Update sensor state
            if entity_id in self._tracked_entities:
                if new_state.state not in ("unknown", "unavailable"):
                    self._sensor_states[entity_id] = new_state.state
                    self._last_updates[entity_id] = datetime.now()
                    # Trigger update
                    self.hass.async_create_task(self.async_request_refresh())

        # Subscribe to state changes
        async_track_state_change_event(
            self.hass,
            list(self._tracked_entities),
            _async_state_changed,
        )

    def get_targets_for_floor(self, floor_id: str | None) -> list[dict[str, Any]]:
        """Get filtered targets for a specific floor."""
        if not self.data:
            return []
        return self.data.get("targets_by_floor", {}).get(floor_id, [])

    def get_floor_data(self, floor_id: str | None) -> dict[str, Any]:
        """Get all data for a specific floor (for service call)."""
        targets = self.get_targets_for_floor(floor_id)

        floor_sensors = [
            {
                "position_x": s.get(CONF_POSITION_X),
                "position_y": s.get(CONF_POSITION_Y),
                "rotation": s.get(CONF_ROTATION),
                "target_entities": s.get(CONF_TARGET_ENTITIES),
                "target_count": sum(
                    1
                    for t in targets
                    if any(
                        e in s.get(CONF_TARGET_ENTITIES, [])
                        for e in t.get("sensor_entities", [])
                    )
                ),
            }
            for s in self.sensors
            if s.get(CONF_FLOOR_ID) == floor_id
        ]

        floor_zones = [
            {
                "name": z.get("name"),
                "vertices": z.get(CONF_VERTICES),
            }
            for z in self.zones
            if z.get(CONF_FLOOR_ID) == floor_id
        ]

        floor_block_zones = [
            {
                "name": z.get("name"),
                "vertices": z.get(CONF_VERTICES),
                "enabled": self._block_zone_states.get(
                    f"switch.{DOMAIN}_{z.get('name', '').lower().replace(' ', '_')}_block",
                    False,
                ),
            }
            for z in self.block_zones
            if z.get(CONF_FLOOR_ID) == floor_id
        ]

        return {
            "floor_id": floor_id,
            "sensors": floor_sensors,
            "zones": floor_zones,
            "block_zones": floor_block_zones,
            "targets": [
                {
                    "x": t["x"],
                    "y": t["y"],
                    "age": t["age_seconds"],
                    "sensor_entities": t.get("sensor_entities", []),
                }
                for t in targets
            ],
        }
