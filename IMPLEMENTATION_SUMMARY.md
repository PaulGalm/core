# Radar Fusion Offset & Calibration Implementation Summary

## Changes Made

### 1. Coordinate System Updated to Lower-Left Origin

**Both Cards** (`radar-fusion-card.js` and `radar-fusion-heatmap-card.js`):
- Changed origin from center (width/2, height/2) to lower-left (5% margin)
- `originX = width * 0.05` (5% from left edge)
- `originY = height * 0.95` (5% from bottom edge)
- This matches typical floorplan orientation

### 2. Configuration Parameters Added

**setConfig() Method**:
```javascript
{
  floorplan_url: config.floorplan_url || null,  // Background image URL
  offset_x: config.offset_x || 0,              // Horizontal shift in mm
  offset_y: config.offset_y || 0,              // Vertical shift in mm
}
```

### 3. Floorplan Image Support

**Both Cards**:
- Added image loading logic in `setConfig()`
- Images are cached in `this._floorplanImage`
- Rendered as background in canvas during drawing
- Supports PNG, JPG, SVG, and other web image formats

### 4. Coordinate Transformation

**toCanvas() Function**:
```javascript
const toCanvas = (x, y) => ({
  x: originX + (x + this._config.offset_x) * scale,
  y: originY - (y + this._config.offset_y) * scale,  // Invert Y
});
```

### 5. Axis Drawing Updated

**Radar Card**:
- X-axis: horizontal line at originY
- Y-axis: vertical line at originX
- Both extend the full grid size
- Maintains 3% opacity for subtle appearance

**Heatmap Card**:
- No explicit axis drawing (heatmap focused)
- Same coordinate transformation applies to heatmap cells

## Files Modified

1. `/config/www/radar-fusion-card.js`
   - Lines 59-77: Updated setConfig with new parameters
   - Lines 268-278: Updated coordinate transformation
   - Lines 280-283: Added floorplan rendering
   - Lines 295-313: Updated axis drawing

2. `/config/www/radar-fusion-heatmap-card.js`
   - Lines 51-68: Updated setConfig with new parameters
   - Lines 203-215: Updated coordinate transformation and floorplan rendering

## Key Features

### Auto-Discovery
- Cards automatically find radar_fusion config entry if not specified
- Works with multiple integrations in same Home Assistant instance

### Flexible Configuration
- All parameters are optional with sensible defaults
- Can be set via YAML or UI (card configuration)
- No changes required to config flow or backend

### Calibration Workflow
1. Add card with floorplan_url
2. Run in test mode to see coordinate system
3. Measure offset from intended position
4. Update offset_x and offset_y
5. Reload card to verify

### Performance Optimized
- Floorplan image cached after first load
- Drawing uses efficient canvas operations
- Offset calculations done during transformation
- No overhead for cards without floorplan

## Testing Recommendations

1. **Coordinate System Verification**
   - Enable grid display
   - Verify 0,0 is at lower-left corner
   - Check axis lines are perpendicular and labeled correctly

2. **Floorplan Rendering**
   - Test with PNG floorplan (simplest format)
   - Verify image displays at full canvas size
   - Check image transparency/alpha is preserved

3. **Offset Calibration**
   - Test positive offsets (right/up movement)
   - Test negative offsets (left/down movement)
   - Verify targets align with floorplan features

4. **Multi-Room Setup**
   - Add multiple cards with different floor_id values
   - Verify each card uses correct offset values
   - Test independence of calibrations

## Backward Compatibility

- All new parameters are optional with defaults
- Existing cards without floorplan/offset continue to work
- No changes to data structures or services
- No database migrations required
- Safe to deploy without integration restart

## Documentation Provided

1. **OFFSET_CALIBRATION.md**: Detailed offset calibration guide
2. **FLOORPLAN_CONFIGURATION.md**: Step-by-step configuration examples
3. Inline code comments in both card files

## Future Enhancement Ideas

1. **UI Controls**: Real-time offset sliders for live adjustment
2. **Auto-Calibration**: Detect reference points and suggest offsets
3. **Multiple Floorplans**: Support different images per room
4. **Scale Detection**: Parse image metadata for automatic scaling
5. **Offset Profiles**: Save/load calibration presets per room
