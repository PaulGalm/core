# Configuration Example for Radar Fusion with Offset Calibration

This example shows how to configure the Radar Fusion cards with floorplan background and offset calibration.

## Step 1: Prepare Your Floorplan

1. Export your floor layout as an image (PNG, JPG recommended)
2. Save it to `/config/www/` directory
3. For example: `/config/www/floorplans/bedroom.png`

## Step 2: Add the Card to Your Dashboard

### Option 1: Via UI (Recommended)

1. Go to your Home Assistant dashboard
2. Click "Edit Dashboard" (pencil icon)
3. Click "Add Card" → "Custom card"
4. Select "Radar Fusion Card" or "Radar Fusion Heatmap Card"
5. Configure the following options:
   - **Title**: Name for your card
   - **Width**: Canvas width in pixels (e.g., 800)
   - **Height**: Canvas height in pixels (e.g., 600)
   - **Grid Size**: Monitoring area in mm (e.g., 5000 for 5 meters)
   - **Show Grid**: Toggle grid display
   - **Floor ID**: Select the room (optional)
   - **Floorplan URL**: `/local/floorplans/bedroom.png`
   - **Offset X**: Horizontal calibration in mm
   - **Offset Y**: Vertical calibration in mm

### Option 2: Manual YAML

Edit your dashboard YAML and add:

```yaml
- type: custom:radar-fusion-card
  title: Bedroom Radar
  width: 800
  height: 600
  grid_size: 5000
  show_grid: true
  floor_id: bedroom
  floorplan_url: /local/floorplans/bedroom.png
  offset_x: 0
  offset_y: 0

- type: custom:radar-fusion-heatmap-card
  title: Detection Heatmap
  width: 800
  height: 600
  grid_size: 5000
  floor_id: bedroom
  floorplan_url: /local/floorplans/bedroom.png
  offset_x: 0
  offset_y: 0
```

## Step 3: Calibrate the Offset

1. **Check Test Mode**: Go to Settings → Devices & Services → Radar Fusion → Configure
   - Toggle "Test Mode" to see simulated movement
   - This helps verify coordinate system alignment

2. **Identify Origin**: Observe where the coordinate system origin (0,0) appears
   - Look for axis lines at the lower-left corner
   - The origin should align with a known point on your floorplan

3. **Measure Displacement**:
   - Determine how far the visualization is from the correct position
   - Measure in millimeters (mm)
   - Direction matters: positive = right/up, negative = left/down

4. **Update Offsets**:
   - If visualization is 500mm too far left → set `offset_x: 500`
   - If visualization is 300mm too far down → set `offset_y: 300`
   - Reload the card to see changes

5. **Iterate**: Adjust incrementally until perfectly aligned

## Step 4: Real-World Setup

Once calibrated, the cards will:
- Display actual sensor data overlaid on your floorplan
- Show detected targets in correct room positions
- Display detection patterns via heatmap

### Multiple Rooms

To monitor different rooms:

```yaml
- type: custom:radar-fusion-card
  title: Bedroom Radar
  floor_id: bedroom
  floorplan_url: /local/floorplans/bedroom.png
  offset_x: 500
  offset_y: 300

- type: custom:radar-fusion-card
  title: Living Room Radar
  floor_id: living_room
  floorplan_url: /local/floorplans/living_room.png
  offset_x: 200
  offset_y: 100
```

## Coordinate System

The cards use a **lower-left origin**:
- **X**: Increases to the right
- **Y**: Increases upward
- **0,0**: Lower-left corner (with 5% margin)

This matches typical architectural floorplans where:
- Bottom-left is the reference point
- Horizontal distance increases to the right
- Vertical distance increases toward the back/top

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Floorplan not visible | Check URL is correct, use `/local/` path |
| Visualization misaligned | Verify offset_x and offset_y are correct |
| Wrong scale | Ensure grid_size matches your room dimensions |
| Grid lines missing | Set `show_grid: true` |
| Targets not showing | Enable test mode or check if radar is detecting |

## Advanced Configuration

### Custom Grid Size

Adjust based on room size:
- Small rooms (e.g., 3m × 3m): `grid_size: 3000`
- Medium rooms (e.g., 5m × 5m): `grid_size: 5000`
- Large rooms (e.g., 8m × 8m): `grid_size: 8000`

### Performance Tuning

If rendering is slow:
- Reduce canvas dimensions (width/height)
- Disable grid display (`show_grid: false`)
- Use a lighter floorplan image (smaller file size)

### Multiple Sensors

If you have multiple Radar Fusion integrations:
- Each card can auto-discover the correct integration
- Or explicitly set `config_entry_id` if needed
- Cards automatically use the configured integration's data
