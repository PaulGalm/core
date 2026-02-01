#!/bin/bash
set -e

# Radar Fusion HACS Sync Script
# This script syncs the radar_fusion integration to a HACS repository with versioning
# Usage: ./sync_radar_fusion_hacs.sh [--patch|--minor|--major|--keep|--version X.Y.Z]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$(dirname "$SCRIPT_DIR")"
INTEGRATION_DIR="$CORE_DIR/homeassistant/components/radar_fusion"
HACS_REPO_DIR="/workspaces/radar-fusion"

echo "🚀 Radar Fusion HACS Sync"
echo "=========================="
echo ""

# Check if manifest.json exists
if [ ! -f "$INTEGRATION_DIR/manifest.json" ]; then
    echo "❌ Error: manifest.json not found at $INTEGRATION_DIR/manifest.json"
    exit 1
fi

# Extract current version from manifest.json
CURRENT_VERSION=$(python3 -c "import json; print(json.load(open('$INTEGRATION_DIR/manifest.json')).get('version', '1.0.0'))")
echo "📦 Current version: $CURRENT_VERSION"
echo ""

# Parse command-line argument
if [ $# -eq 0 ]; then
    # Interactive mode
    echo "Version bump options:"
    echo "  1) Patch (${CURRENT_VERSION%.*}.$((${CURRENT_VERSION##*.} + 1)))"
    echo "  2) Minor (${CURRENT_VERSION%.*.*}.$((${CURRENT_VERSION#*.*.} + 1)).0)"
    echo "  3) Major ($((${CURRENT_VERSION%%.*.*} + 1)).0.0)"
    echo "  4) Custom version"
    echo "  5) Keep current version ($CURRENT_VERSION)"
    echo ""
    read -p "Select option [1-5]: " VERSION_OPTION

    case $VERSION_OPTION in
        1)
            VERSION_ARG="--patch"
            ;;
        2)
            VERSION_ARG="--minor"
            ;;
        3)
            VERSION_ARG="--major"
            ;;
        4)
            read -p "Enter custom version (e.g., 1.2.3): " CUSTOM_VERSION
            VERSION_ARG="--version $CUSTOM_VERSION"
            ;;
        5)
            VERSION_ARG="--keep"
            ;;
        *)
            echo "❌ Invalid option"
            exit 1
            ;;
    esac
else
    VERSION_ARG="$1 $2"
fi

# Determine new version based on argument
case "$1" in
    --patch)
        NEW_VERSION="${CURRENT_VERSION%.*}.$((${CURRENT_VERSION##*.} + 1))"
        ;;
    --minor)
        MAJOR="${CURRENT_VERSION%%.*}"
        MINOR="${CURRENT_VERSION#*.}"
        MINOR="${MINOR%.*}"
        NEW_VERSION="${MAJOR}.$((MINOR + 1)).0"
        ;;
    --major)
        MAJOR="${CURRENT_VERSION%%.*}"
        NEW_VERSION="$((MAJOR + 1)).0.0"
        ;;
    --version)
        if [ -z "$2" ]; then
            echo "❌ Error: --version requires a version number (e.g., --version 1.2.3)"
            exit 1
        fi
        NEW_VERSION="$2"
        ;;
    --keep)
        NEW_VERSION="$CURRENT_VERSION"
        ;;
    "")
        # Already handled in interactive mode above
        ;;
    *)
        echo "❌ Error: Unknown option '$1'"
        echo "Usage: $0 [--patch|--minor|--major|--keep|--version X.Y.Z]"
        exit 1
        ;;
esac

echo ""
echo "📝 New version: $NEW_VERSION"
echo ""

# Update version in manifest.json if changed
if [ "$NEW_VERSION" != "$CURRENT_VERSION" ]; then
    echo "✏️  Updating manifest.json version..."
    python3 << PYTHON
import json

manifest_path = "$INTEGRATION_DIR/manifest.json"
with open(manifest_path, 'r') as f:
    manifest = json.load(f)

manifest['version'] = "$NEW_VERSION"

with open(manifest_path, 'w') as f:
    json.dump(manifest, f, indent=2)
    f.write('\n')

print(f"✅ Updated manifest.json to version $NEW_VERSION")
PYTHON
else
    echo "ℹ️  Version unchanged"
fi

# Create HACS repository directory if it doesn't exist
if [ ! -d "$HACS_REPO_DIR" ]; then
    echo ""
    echo "📁 Creating HACS repository directory..."
    mkdir -p "$HACS_REPO_DIR"
    cd "$HACS_REPO_DIR"
    git init
    echo "✅ Initialized git repository"
else
    cd "$HACS_REPO_DIR"
    if [ ! -d ".git" ]; then
        echo "⚠️  Directory exists but is not a git repository. Initializing..."
        git init
    fi
fi

echo ""
echo "📋 Copying integration files..."

# Create custom_components directory structure
mkdir -p custom_components/radar_fusion

# Copy all integration files
rsync -av --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
    "$INTEGRATION_DIR/" custom_components/radar_fusion/

echo "✅ Copied integration files"

# Create hacs.json if it doesn't exist
if [ ! -f "hacs.json" ]; then
    echo ""
    echo "📄 Creating hacs.json..."
    cat > hacs.json << 'EOF'
{
  "name": "Radar Fusion",
  "render_readme": true,
  "homeassistant": "2024.1.0"
}
EOF
    echo "✅ Created hacs.json"
fi

# Create README.md if it doesn't exist
if [ ! -f "README.md" ]; then
    echo ""
    echo "📄 Creating README.md..."
    cat > README.md << 'EOF'
# Radar Fusion for Home Assistant

Multi-sensor radar fusion for presence detection with ESPHome LD2450 sensors.

## Features

- 🎯 Fuse multiple LD2450 sensors for complete coverage
- 📍 Create custom detection zones with polygon vertices
- 🚫 Filter false positives with block zones
- 🗺️ Organize by floor
- 🔥 Track presence patterns with heatmaps
- 🎨 Includes visualization cards for Lovelace dashboard

## Requirements

- Home Assistant 2024.1.0+
- ESPHome LD2450 sensors with target entities:
  - `sensor.device_target{1-3}_{x,y}`

## Installation via HACS

1. Add this repository as a custom repository in HACS:
   - Go to HACS → Integrations → ⋮ (menu) → Custom repositories
   - Repository: `https://github.com/YOUR_USERNAME/radar-fusion`
   - Category: Integration
2. Click "Explore & Download Repositories"
3. Search for "Radar Fusion"
4. Click "Download"
5. Restart Home Assistant
6. Add integration via Settings → Devices & Services → Add Integration → Radar Fusion

## Lovelace Cards

The integration includes two custom Lovelace cards:

### Radar Fusion Card
Visualizes sensor coverage, zones, and detected targets in real-time.

**Add resource:**
Settings → Dashboards → Resources → Add Resource
- URL: `/radar_fusion_static/radar-fusion-card.js`
- Type: JavaScript Module

**Example configuration:**
```yaml
type: custom:radar-fusion-card
config_entry_id: YOUR_CONFIG_ENTRY_ID
floor_id: ground_floor  # optional
```

### Radar Fusion Heatmap Card
Displays presence heatmap showing where movement is detected over time.

**Add resource:**
Settings → Dashboards → Resources → Add Resource
- URL: `/radar_fusion_static/radar-fusion-heatmap-card.js`
- Type: JavaScript Module

**Example configuration:**
```yaml
type: custom:radar-fusion-heatmap-card
config_entry_id: YOUR_CONFIG_ENTRY_ID
floor_id: ground_floor  # optional
```

## Configuration

1. Add integration via UI
2. Configure sensors (position, rotation, offset calibration)
3. Create zones with JSON vertices: `[[x1,y1], [x2,y2], ...]`
4. Optional: Add block zones for filtering false positives

## Services

- `radar_fusion.get_floor_data` - Get sensor/zone/target data for visualization
- `radar_fusion.reset_heatmap` - Clear heatmap data
- `radar_fusion.set_test_mode` - Toggle test mode

## Development

This integration is developed in the [home-assistant/core](https://github.com/home-assistant/core) repository on a custom branch and synced to this HACS distribution repository.
EOF
    echo "✅ Created README.md"
    echo "⚠️  Remember to update YOUR_USERNAME in README.md with your GitHub username!"
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo ""
    echo "📄 Creating .gitignore..."
    cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*$py.class
*.so
.DS_Store
.vscode/
*.swp
*~
.pytest_cache/
EOF
    echo "✅ Created .gitignore"
fi

# Git operations
echo ""
echo "📦 Committing changes..."

git add .

if git diff --staged --quiet; then
    echo "ℹ️  No changes to commit"
else
    git commit -m "Sync radar_fusion v$NEW_VERSION" \
               -m "Updated integration to version $NEW_VERSION" \
               -m "" \
               -m "Includes:" \
               -m "- Integration code in custom_components/radar_fusion/" \
               -m "- Frontend cards served at /radar_fusion_static/"
    echo "✅ Committed changes"

    # Create git tag if version changed
    if [ "$NEW_VERSION" != "$CURRENT_VERSION" ]; then
        TAG_NAME="v$NEW_VERSION"

        # Check if tag already exists
        if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
            echo "⚠️  Tag $TAG_NAME already exists"
            read -p "Do you want to delete and recreate it? [y/N]: " RECREATE_TAG
            if [ "$RECREATE_TAG" = "y" ] || [ "$RECREATE_TAG" = "Y" ]; then
                git tag -d "$TAG_NAME"
                git tag -a "$TAG_NAME" -m "Release $NEW_VERSION"
                echo "✅ Recreated tag $TAG_NAME"
            fi
        else
            git tag -a "$TAG_NAME" -m "Release $NEW_VERSION"
            echo "✅ Created tag $TAG_NAME"
        fi
    fi
fi

echo ""
echo "✅ HACS repository synced successfully!"
echo ""
echo "📍 Repository location: $HACS_REPO_DIR"
echo "📌 Version: $NEW_VERSION"
echo ""
echo "📝 Next steps:"
echo "1. Review changes in $HACS_REPO_DIR"
echo "2. If this is your first sync, create GitHub repository:"
echo "   cd $HACS_REPO_DIR"
echo "   gh repo create radar-fusion --public --source=. --remote=origin"
echo ""
echo "3. Push to GitHub:"
echo "   cd $HACS_REPO_DIR"
echo "   git push -u origin main"
echo "   git push --tags"
echo ""
echo "4. Add to HACS:"
echo "   - HACS → Integrations → ⋮ → Custom repositories"
echo "   - Repository: https://github.com/YOUR_USERNAME/radar-fusion"
echo "   - Category: Integration"
echo ""
