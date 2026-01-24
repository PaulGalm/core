# Radar Fusion - Device Selector Changes

## Summary

Updated the Radar Fusion integration to use a device selector instead of manual entity selection. The integration now automatically detects all 6 target coordinate entities from the selected LD2450 device.

## Changes Made

### 1. Config Flow (`config_flow.py`)

#### Added Helper Method
```python
def _get_target_entities_from_device(self, device_id: str) -> list[str]:
    """Get target entities from a device."""
    entity_registry = er.async_get(self.hass)
    target_entities = []

    # Find all entities for this device
    entities = er.async_entries_for_device(entity_registry, device_id)

    # Look for target entities (target1_x, target1_y, target2_x, etc.)
    for entity in entities:
        if entity.domain == "sensor" and entity.entity_id:
            entity_id = entity.entity_id
            # Check if it matches the target pattern
            if "target" in entity_id.lower() and (
                entity_id.endswith("_x") or entity_id.endswith("_y")
            ):
                target_entities.append(entity_id)

    # Sort to ensure consistent order: target1_x, target1_y, target2_x, etc.
    target_entities.sort()
    return target_entities
```

#### Updated Form Schema
**Before:**
```python
vol.Required(CONF_TARGET_ENTITIES): selector.EntitySelector(
    selector.EntitySelectorConfig(
        domain="sensor",
        multiple=True,
    )
)
```

**After:**
```python
vol.Required("device_id"): selector.DeviceSelector(
    selector.DeviceSelectorConfig(
        entity=[
            selector.EntityFilterSelectorConfig(domain="sensor")
        ]
    )
)
```

#### Updated Validation Logic
**Before:**
```python
target_entities = user_input[CONF_TARGET_ENTITIES]
if len(target_entities) != 6:
    errors["base"] = "invalid_target_count"
```

**After:**
```python
device_id = user_input["device_id"]
target_entities = self._get_target_entities_from_device(device_id)

if not target_entities:
    errors["base"] = "no_target_entities"
elif len(target_entities) != 6:
    errors["base"] = "invalid_target_count"
```

### 2. Strings (`strings.json`)

#### Updated Error Messages
- Changed `invalid_target_count` message to reflect device-based validation
- Added new `no_target_entities` error message

#### Updated Form Descriptions
**Before:**
- Required manual selection of 6 entities
- Listed all entity types (target1_x, target1_y, etc.)

**After:**
- Simple device selection
- Automatic entity detection
- Clearer user instructions

### 3. Mock Sensors (`configuration.yaml`)

Updated template sensor names to match standard LD2450 format:

**Before:**
- `test_radar_1_target_1_x`
- `test_radar_1_target_1_y`
- etc.

**After:**
- `sensor.ld2450_target1_x`
- `sensor.ld2450_target1_y`
- `sensor.ld2450_target2_x`
- `sensor.ld2450_target2_y`
- `sensor.ld2450_target3_x`
- `sensor.ld2450_target3_y`

## Benefits

1. **Simpler UX**: Users only need to select the device, not 6 individual entities
2. **Less Error-Prone**: Automatic detection ensures correct entities are selected
3. **Standard Format**: Mock sensors now match real LD2450 naming convention
4. **Better Validation**: Clear error messages for missing or incorrect entity counts

## Testing

To test with the mock sensors:

1. Add the Radar Fusion integration
2. Select "Template" as the device
3. The integration will automatically detect all 6 target coordinate entities
4. Configure position and rotation as needed

## Entity Detection Pattern

The auto-detection looks for entities matching:
- Domain: `sensor`
- Name contains: `target`
- Ends with: `_x` or `_y`

Example matches:
- ✅ `sensor.ld2450_target1_x`
- ✅ `sensor.my_device_target2_y`
- ❌ `sensor.temperature`
- ❌ `binary_sensor.target1_x`
