class RadarFusionCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = null;
    this._showZones = true;
    this._showSensors = true;
    this._showDetectionZones = true;
    this._sensorColors = [
      '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
      '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788'
    ];
    this._heatmapScale = 'hourly'; // 'hourly' | '24h' | 'all_time'
  }

  setConfig(config) {
    this._config = {
      config_entry_id: config.config_entry_id || null,  // Auto-discover if not provided
      width: config.width || 800,
      height: config.height || 600,
      grid_size: config.grid_size || 5000, // mm
      show_grid: config.show_grid !== false,
      floor_id: config.floor_id || null,
      title: config.title || 'Radar Fusion',
    };
  }

  async discoverConfigEntry() {
    // Auto-discover radar_fusion config entry
    if (this._config.config_entry_id) return this._config.config_entry_id;

    try {
      console.log('Radar Fusion: Attempting auto-discovery...');

      // Look for any radar_fusion entity
      const states = this._hass.states;
      for (const entityId in states) {
        const state = states[entityId];
        // Check if entity belongs to radar_fusion
        if ((entityId.startsWith('binary_sensor.') || entityId.startsWith('switch.')) &&
            state.attributes.attribution === 'Radar Fusion') {

          const entityInfo = await this._hass.connection.sendMessagePromise({
            type: 'config/entity_registry/get',
            entity_id: entityId,
          });

          if (entityInfo && entityInfo.config_entry_id) {
            this._config.config_entry_id = entityInfo.config_entry_id;
            console.log('Radar Fusion: Auto-discovered →', entityInfo.config_entry_id);
            return entityInfo.config_entry_id;
          }
        }
      }

      console.warn('Radar Fusion: No entities found. Please add sensors or zones first.');
    } catch (error) {
      console.error('Radar Fusion: Discovery failed:', error);
    }

    return null;
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  async updateCard() {
    if (!this._hass) return;

    // Auto-discover config entry if not set
    if (!this._config.config_entry_id) {
      const discovered = await this.discoverConfigEntry();
      if (!discovered) {
        this.renderError('No Radar Fusion integration found. Please add it in Settings → Devices & Services.');
        return;
      }
    }

    this.render();
  }

  render() {
    const style = `
      <style>
        :host {
          display: block;
          padding: 16px;
        }
        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }
        .card-title {
          font-size: 20px;
          font-weight: 500;
        }
        .controls {
          display: flex;
          gap: 12px;
        }
        .toggle-btn {
          padding: 6px 12px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          background: var(--card-background-color);
          cursor: pointer;
          font-size: 12px;
          transition: all 0.2s;
        }
        .toggle-btn.active {
          background: var(--primary-color);
          color: var(--text-primary-color);
          border-color: var(--primary-color);
        }
        .canvas-container {
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          overflow: hidden;
          background: #1a1a1a;
          position: relative;
          width: 100%;
        }
        canvas {
          display: block;
          width: 100%;
          height: auto;
        }
        .legend {
          margin-top: 12px;
          display: flex;
          flex-wrap: wrap;
          gap: 16px;
          font-size: 12px;
        }
        .legend-item {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .legend-color {
          width: 16px;
          height: 16px;
          border-radius: 2px;
        }
        .stats {
          margin-top: 12px;
          font-size: 12px;
          color: var(--secondary-text-color);
        }
      </style>
    `;

    const html = `
      ${style}
      <div class="card-header">
        <div class="card-title">${this._config.title}</div>
        <div class="controls">
            <select id="heatmap-scale" class="toggle-btn">
              <option value="hourly">Heatmap: hourly</option>
              <option value="24h">Heatmap: 24h</option>
              <option value="all_time">Heatmap: all-time</option>
            </select>
            <button class="toggle-btn" id="reset-heatmap">Reset heatmap</button>
          <button class="toggle-btn ${this._showZones ? 'active' : ''}" id="toggle-zones">
            Zones
          </button>
          <button class="toggle-btn ${this._showSensors ? 'active' : ''}" id="toggle-sensors">
            Sensors
          </button>
          <button class="toggle-btn ${this._showDetectionZones ? 'active' : ''}" id="toggle-detection">
            Detection Zones
          </button>
        </div>
      </div>
      <div class="canvas-container">
        <canvas id="radarCanvas" width="${this._config.width}" height="${this._config.height}"></canvas>
      </div>
      <div class="legend" id="legend"></div>
      <div class="stats" id="stats"></div>
    `;

    this.shadowRoot.innerHTML = html;

    // Add event listeners
    this.shadowRoot.getElementById('toggle-zones').addEventListener('click', () => {
      this._showZones = !this._showZones;
      this.updateCard();
    });
    this.shadowRoot.getElementById('toggle-sensors').addEventListener('click', () => {
      this._showSensors = !this._showSensors;
      this.updateCard();
    });
    this.shadowRoot.getElementById('toggle-detection').addEventListener('click', () => {
      this._showDetectionZones = !this._showDetectionZones;
      this.updateCard();
    });

    // Heatmap controls
    this.shadowRoot.getElementById('heatmap-scale').value = this._heatmapScale;
    this.shadowRoot.getElementById('heatmap-scale').addEventListener('change', (ev) => {
      this._heatmapScale = ev.target.value;
      this.updateCard();
    });
    this.shadowRoot.getElementById('reset-heatmap').addEventListener('click', async () => {
      await this.resetHeatmap();
      this.updateCard();
    });

    this.drawRadar();
  }

  async drawRadar() {
    const canvas = this.shadowRoot.getElementById('radarCanvas');
    const statsEl = this.shadowRoot.getElementById('stats');

    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, width, height);

    // Get data from service call
    const data = await this.getFloorData();

    console.log('Floor data received:', JSON.stringify(data, null, 2));

    if (!data) {
      // Show message on canvas
      ctx.fillStyle = '#999';
      ctx.font = '16px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Unable to load radar data', width / 2, height / 2 - 20);
      ctx.font = '14px sans-serif';
      ctx.fillText('Check console for errors', width / 2, height / 2 + 10);
      if (statsEl) statsEl.textContent = 'No data available';
      return;
    }

    // Check if there's any configuration
    const hasSensors = data.sensors && data.sensors.length > 0;
    const hasZones = data.zones && data.zones.length > 0;

    if (!hasSensors && !hasZones) {
      ctx.fillStyle = '#ff9800';
      ctx.font = '18px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('⚙️ Setup Required', width / 2, height / 2 - 40);
      ctx.font = '14px sans-serif';
      ctx.fillStyle = '#999';
      ctx.fillText('No sensors or zones configured', width / 2, height / 2 - 10);
      ctx.fillText('Go to Settings → Devices & Services', width / 2, height / 2 + 15);
      ctx.fillText('Click "Configure" on Radar Fusion', width / 2, height / 2 + 40);
      if (statsEl) statsEl.textContent = 'Please add sensors and zones in the integration settings';
      return;
    }

    const gridSize = this._config.grid_size;
    const scale = Math.min(width / gridSize, height / gridSize) * 0.9;
    const offsetX = width / 2;
    const offsetY = height / 2;

    // Helper function to convert mm coordinates to canvas
    const toCanvas = (x, y) => ({
      x: offsetX + x * scale,
      y: offsetY - y * scale, // Invert Y for canvas
    });

    // Draw grid
    if (this._config.show_grid) {
      ctx.strokeStyle = '#2a2a2a';
      ctx.lineWidth = 1;
      const gridStep = 1000; // 1 meter
      for (let x = -gridSize / 2; x <= gridSize / 2; x += gridStep) {
        const pos = toCanvas(x, 0);
        ctx.beginPath();
        ctx.moveTo(pos.x, 0);
        ctx.lineTo(pos.x, height);
        ctx.stroke();
      }
      for (let y = -gridSize / 2; y <= gridSize / 2; y += gridStep) {
        const pos = toCanvas(0, y);
        ctx.beginPath();
        ctx.moveTo(0, pos.y);
        ctx.lineTo(width, pos.y);
        ctx.stroke();
      }

      // Draw center axes
      ctx.strokeStyle = '#3a3a3a';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(offsetX, 0);
      ctx.lineTo(offsetX, height);
      ctx.moveTo(0, offsetY);
      ctx.lineTo(width, offsetY);
      ctx.stroke();
    }

    // Draw zones (polygons)
    if (this._showZones && data.zones) {
      data.zones.forEach((zone) => {
        if (zone.vertices && zone.vertices.length >= 3) {
          ctx.fillStyle = 'rgba(76, 175, 80, 0.2)';
          ctx.strokeStyle = 'rgba(76, 175, 80, 0.8)';
          ctx.lineWidth = 2;

          ctx.beginPath();
          const first = toCanvas(zone.vertices[0][0], zone.vertices[0][1]);
          ctx.moveTo(first.x, first.y);
          for (let i = 1; i < zone.vertices.length; i++) {
            const point = toCanvas(zone.vertices[i][0], zone.vertices[i][1]);
            ctx.lineTo(point.x, point.y);
          }
          ctx.closePath();
          ctx.fill();
          ctx.stroke();

          // Draw zone name
          const center = this.getPolygonCenter(zone.vertices);
          const centerCanvas = toCanvas(center.x, center.y);
          ctx.fillStyle = '#4CAF50';
          ctx.font = '14px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(zone.name, centerCanvas.x, centerCanvas.y);
        }
      });
    }

    // Draw block zones
    if (this._showDetectionZones && data.block_zones) {
      data.block_zones.forEach((zone) => {
        if (zone.vertices && zone.vertices.length >= 3) {
          ctx.fillStyle = 'rgba(244, 67, 54, 0.2)';
          ctx.strokeStyle = 'rgba(244, 67, 54, 0.8)';
          ctx.lineWidth = 2;
          ctx.setLineDash([5, 5]);

          ctx.beginPath();
          const first = toCanvas(zone.vertices[0][0], zone.vertices[0][1]);
          ctx.moveTo(first.x, first.y);
          for (let i = 1; i < zone.vertices.length; i++) {
            const point = toCanvas(zone.vertices[i][0], zone.vertices[i][1]);
            ctx.lineTo(point.x, point.y);
          }
          ctx.closePath();
          ctx.fill();
          ctx.stroke();
          ctx.setLineDash([]);

          // Draw zone name
          const center = this.getPolygonCenter(zone.vertices);
          const centerCanvas = toCanvas(center.x, center.y);
          ctx.fillStyle = '#F44336';
          ctx.font = '12px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(zone.name + ' (blocked)', centerCanvas.x, centerCanvas.y);
        }
      });
    }

    // Draw sensors and detection zones
    if (data.sensors) {
      const legend = this.shadowRoot.getElementById('legend');
      legend.innerHTML = '';

      data.sensors.forEach((sensor, idx) => {
        const color = this._sensorColors[idx % this._sensorColors.length];

        // Draw detection zone (6m range, 120° cone for LD2450)
        if (this._showDetectionZones) {
          const range = 6000; // 6 meters in mm
          const angle = 120; // degrees total (±60°)
          const rotation = sensor.rotation || 0;

          ctx.fillStyle = color + '20';
          ctx.strokeStyle = color + '80';
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 3]);

          const sensorPos = toCanvas(sensor.position_x, sensor.position_y);
          ctx.beginPath();
          ctx.moveTo(sensorPos.x, sensorPos.y);

          // Draw cone
          const startAngle = (rotation - angle / 2) * Math.PI / 180;
          const endAngle = (rotation + angle / 2) * Math.PI / 180;

          for (let a = startAngle; a <= endAngle; a += 0.1) {
            const x = sensor.position_x + range * Math.cos(a + Math.PI / 2);
            const y = sensor.position_y + range * Math.sin(a + Math.PI / 2);
            const pos = toCanvas(x, y);
            ctx.lineTo(pos.x, pos.y);
          }
          ctx.closePath();
          ctx.fill();
          ctx.stroke();
          ctx.setLineDash([]);
        }

        // Draw sensor position
        if (this._showSensors) {
          const sensorPos = toCanvas(sensor.position_x, sensor.position_y);

          // Sensor marker
          ctx.fillStyle = color;
          ctx.strokeStyle = '#fff';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(sensorPos.x, sensorPos.y, 10, 0, 2 * Math.PI);
          ctx.fill();
          ctx.stroke();

          // Direction indicator
          const rotation = sensor.rotation || 0;
          const dirLength = 20;
          const dirAngle = (rotation + 90) * Math.PI / 180;
          const dirX = sensorPos.x + dirLength * Math.cos(dirAngle);
          const dirY = sensorPos.y - dirLength * Math.sin(dirAngle);

          ctx.strokeStyle = color;
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.moveTo(sensorPos.x, sensorPos.y);
          ctx.lineTo(dirX, dirY);
          ctx.stroke();

          // Sensor label
          ctx.fillStyle = '#fff';
          ctx.font = '10px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(`S${idx + 1}`, sensorPos.x, sensorPos.y - 18);
        }

        // Add to legend
        const legendItem = document.createElement('div');
        legendItem.className = 'legend-item';
        legendItem.innerHTML = `
          <div class="legend-color" style="background: ${color}"></div>
          <span>Sensor ${idx + 1} (${sensor.target_count || 0} targets)</span>
        `;
        legend.appendChild(legendItem);
      });
    }

    // Draw targets
    if (data.targets && data.targets.length > 0) {
      console.log('Drawing targets:', data.targets.length, data.targets);
      data.targets.forEach((target) => {
        // Skip invalid targets
        if (target.x === -1 || target.y === -1) {
          return;
        }

        const sensorIdx = data.sensors.findIndex(s =>
          target.sensor_entities && s.target_entities &&
          s.target_entities.some(e => target.sensor_entities.includes(e))
        );
        const color = this._sensorColors[sensorIdx >= 0 ? sensorIdx : 0];

        const pos = toCanvas(target.x, target.y);

        console.log(`Target at (${target.x}, ${target.y}) -> canvas (${pos.x}, ${pos.y}), color: ${color}`);

        // Draw target
        ctx.fillStyle = color;
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 6, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();

        // Draw target trail/motion indicator
        if (target.age !== undefined && target.age < 5) {
          const alpha = 1 - (target.age / 5);
          ctx.fillStyle = color + Math.floor(alpha * 255).toString(16).padStart(2, '0');
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, 8 + target.age * 2, 0, 2 * Math.PI);
          ctx.fill();
        }
      });
    }

    // Draw heatmap overlay (after targets so it shows beneath if desired)
    if (data.heatmap) {
      const heatmapData = data.heatmap;
      const timeline = this._heatmapScale === 'hourly' ? heatmapData.hourly : (this._heatmapScale === '24h' ? heatmapData['24h'] : heatmapData.all_time);
      const entries = Object.entries(timeline || {});
      if (entries.length > 0) {
        // Determine max for normalization
        let maxCount = 0;
        entries.forEach(([k, v]) => { if (v > maxCount) maxCount = v; });
        ctx.save();
        ctx.globalCompositeOperation = 'lighter';
        entries.forEach(([k, v]) => {
          const parts = k.split('_');
          const xi = parseInt(parts[0], 10);
          const yi = parseInt(parts[1], 10);
          const xCenter = (xi + 0.5) * (this._config.grid_size / (this._config.grid_size / (this._config.grid_size))); // placeholder mm calc
          const yCenter = (yi + 0.5) * (this._config.grid_size / (this._config.grid_size / (this._config.grid_size)));
          // Better: compute center from bin*HEATMAP_RES_MM
          const RES_MM = (heatmapData.resolution_mm || 500);
          const cx_mm = (xi + 0.5) * RES_MM;
          const cy_mm = (yi + 0.5) * RES_MM;
          const cpos = toCanvas(cx_mm, cy_mm);
          const size = RES_MM * scale;
          const intensity = Math.min(1, (v / Math.max(1, maxCount)));
          // Color from green->red
          const hue = (1 - intensity) * 120; // 120 green -> 0 red
          ctx.fillStyle = `hsla(${hue}, 100%, 50%, ${0.25 * intensity + 0.05})`;
          ctx.fillRect(cpos.x - size / 2, cpos.y - size / 2, size, size);
        });
        ctx.restore();
      }
    }

    // Update stats
    const totalTargets = data.targets?.length || 0;
    const activeSensors = data.sensors?.filter(s => s.target_count > 0).length || 0;
    const totalZones = data.zones?.length || 0;
    if (statsEl) {
      statsEl.textContent = `${totalTargets} active targets • ${activeSensors}/${data.sensors?.length || 0} sensors • ${totalZones} zones`;
    }
  }

  getPolygonCenter(vertices) {
    let x = 0, y = 0;
    vertices.forEach(v => {
      x += v[0];
      y += v[1];
    });
    return { x: x / vertices.length, y: y / vertices.length };
  }

  async getFloorData() {
    try {
      // Auto-discover config entry if needed
      const configEntryId = await this.discoverConfigEntry();
      if (!configEntryId) {
        console.error('No radar_fusion config entry found');
        return null;
      }

      console.log('Calling get_floor_data service with config_entry_id:', configEntryId);

      // Call the service using hass.callWS
      const result = await this._hass.callWS({
        type: 'call_service',
        domain: 'radar_fusion',
        service: 'get_floor_data',
        service_data: {
          config_entry_id: configEntryId,
          floor_id: this._config.floor_id || null,
        },
        return_response: true,
      });

      console.log('Received floor data:', result);
      return result.response;
    } catch (error) {
      console.error('Failed to get floor data:', error);
      return null;
    }
  }

  async resetHeatmap() {
    try {
      const configEntryId = await this.discoverConfigEntry();
      if (!configEntryId) return null;

      await this._hass.callWS({
        type: 'call_service',
        domain: 'radar_fusion',
        service: 'reset_heatmap',
        service_data: {
          config_entry_id: configEntryId,
          floor_id: this._config.floor_id || null,
        },
      });
      return true;
    } catch (err) {
      console.error('Failed to reset heatmap:', err);
      return false;
    }
  }

  renderError(message) {
    this.shadowRoot.innerHTML = `
      <style>
        .error-container {
          padding: 16px;
          text-align: center;
        }
        .error-title {
          color: var(--error-color);
          font-size: 18px;
          margin-bottom: 12px;
        }
        .error-message {
          color: var(--secondary-text-color);
          font-size: 14px;
          margin-bottom: 8px;
        }
        .error-help {
          color: var(--primary-color);
          font-size: 12px;
          margin-top: 16px;
        }
      </style>
      <div class="error-container">
        <div class="error-title">⚠️ Radar Fusion</div>
        <div class="error-message">${message}</div>
        <div class="error-help">
          💡 Make sure the integration is installed and configured<br>
          Settings → Devices & Services → Add Integration → Radar Fusion
        </div>
      </div>
    `;
  }

  getCardSize() {
    return 5;
  }
}

customElements.define('radar-fusion-card', RadarFusionCard);

// Register with custom cards registry
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'radar-fusion-card',
  name: 'Radar Fusion Card',
  description: 'Visualize radar sensors, zones, and detected targets',
  preview: true,
});

console.info(
  '%c RADAR-FUSION-CARD %c v1.0.0 ',
  'color: white; background: #4CAF50; font-weight: bold;',
  'color: #4CAF50; background: white; font-weight: bold;',
);
