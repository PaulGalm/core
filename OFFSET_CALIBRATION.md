# Radar Fusion Offset Calibration & Coordinate System

## Overview
The Radar Fusion integration now supports configurable offset parameters and floorplan background rendering to help align the visualization with actual floor layouts.

## Coordinate System
The visualization now uses a **lower-left origin** (0,0 at lower-left corner), which is more intuitive for floorplan alignment:
- **X-axis**: Horizontal, increases to the right
- **Y-axis**: Vertical, increases upward
- **Origin**: Lower-left corner of the canvas with 5% margin for axes
- Canvas coordinate system: Inverted Y (standard HTML canvas) with transformation for proper rendering

## Configuration Parameters

### `offset_x` (in mm)
- **Type**: Number (default: 0)
- **Purpose**: Horizontal shift to align visualization with floorplan
- **Positive values**: Shift visualization to the right
- **Negative values**: Shift visualization to the left
- **Example**: If your sensor is mounted 500mm to the left of the floorplan origin, set `offset_x: 500`

### `offset_y` (in mm)
- **Type**: Number (default: 0)
- **Purpose**: Vertical shift to align visualization with floorplan
- **Positive values**: Shift visualization upward
- **Negative values**: Shift visualization downward
- **Example**: If your sensor is mounted 300mm below the floorplan origin, set `offset_y: -300`

### `floorplan_url` (optional)
- **Type**: String (URL)
- **Purpose**: Background image for floorplan visualization
- **Supported formats**: PNG, JPG, SVG, etc.
- **Example**: `https://example.com/floorplan.png` or local file URL

## Card Configuration Example

### Radar Fusion Card
```yaml
type: custom:radar-fusion-card
title: Radar Fusion
config_entry_id: radar_fusion_entry_id
width: 800
height: 600
grid_size: 5000
show_grid: true
floor_id: bedroom
floorplan_url: /local/floorplans/bedroom.png
offset_x: 500
offset_y: 300
```

### Radar Fusion Heatmap Card
```yaml
type: custom:radar-fusion-heatmap-card
title: Detection Heatmap
config_entry_id: radar_fusion_entry_id
width: 800
height: 600
grid_size: 5000
floor_id: bedroom
floorplan_url: /local/floorplans/bedroom.png
offset_x: 500
offset_y: 300
```

## Calibration Workflow

1. **Prepare Floorplan Image**
   - Export or capture your floor layout as an image (PNG/JPG recommended)
   - Place it in Home Assistant's `www` directory (accessible via `/local/`)
   - Note the scale: 1 pixel = ? mm

2. **Initial Setup**
   - Add the card to your dashboard without offset values (use defaults)
   - Set `floorplan_url` to your floorplan image
   - Run the integration in test mode to see target movement

3. **Alignment**
   - Observe where the visualization origin (0,0) appears on the floorplan
   - Measure the displacement (offset) from the intended position
   - Update `offset_x` and `offset_y` accordingly

4. **Fine-Tuning**
   - Start with rough estimates of offset values
   - Reload the card to see changes
   - Adjust incrementally until visualization aligns with floorplan
   - Record final offset values for reference

## Implementation Details

### Radar Fusion Card (`/config/www/radar-fusion-card.js`)
- Updated `setConfig()` to accept `floorplan_url`, `offset_x`, `offset_y`
- Modified `toCanvas()` coordinate transformation to use lower-left origin
- Added floorplan image rendering in `drawRadar()`
- Updated axis drawing to reflect new coordinate system

### Heatmap Card (`/config/www/radar-fusion-heatmap-card.js`)
- Mirror implementation of offset and floorplan support
- Consistent coordinate system across both visualizations
- Identical calibration parameters

### Coordinate Transformation
```javascript
// Lower-left origin with 5% margin
const originX = width * 0.05;
const originY = height * 0.95;

const toCanvas = (x, y) => ({
  x: originX + (x + offset_x) * scale,
  y: originY - (y + offset_y) * scale,
});
```

## Tips & Troubleshooting

### Floorplan Not Showing
- Verify URL is correct and accessible
- Check browser console for CORS errors
- Use local files (`/local/`) for simplicity

### Visualization Not Aligned
- Double-check offset_x and offset_y values
- Verify grid size matches your floorplan scale
- Ensure floorplan is correctly oriented (0,0 should be lower-left)

### Negative Offsets
- If your sensor is to the right/above the floorplan origin, use negative values
- If your sensor is to the left/below the floorplan origin, use positive values

### Grid Display
- Grid lines now align with the lower-left coordinate system
- Grid spacing is 1 meter (1000 mm) by default
- Disable with `show_grid: false` if it obscures visualization

## Future Enhancements
- Real-time offset adjustment UI controls
- Multiple floorplan support per room
- Automatic scale detection from floorplan metadata
- Offset presets/profiles for different rooms
