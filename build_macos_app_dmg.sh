#!/usr/bin/env bash
# Build a macOS .app and .dmg from a Python project using PyInstaller.
# Usage:
#   ./build_macos_app_dmg.sh -n "MyApp" -e path/to/main.py -i assets/icon.png -b com.example.myapp -v 1.0.0 --add-data "data/:data/"
#
# Notes:
# - Requires macOS. Ensure Python 3 and PyInstaller are installed: python3 -m pip install pyinstaller
# - Icon can be .icns or .png (this script can convert PNG -> ICNS using sips + iconutil).
# - For --add-data, use the format 'SRC:DEST' (colon on macOS), e.g. "assets/:assets/".
# - The resulting .app lives under dist/, and a compressed DMG is created in the output directory (default: dist).
# - Optional: --adhoc-sign will ad-hoc sign the .app (not notarized).

set -euo pipefail

APP_NAME="PhraseTools"
ENTRY_POINT="main_merged_qt5.py"
ICON_PATH="ico.png"
OUTDIR="dist"
BUNDLE_ID="com.phrase_tools.app"
VERSION="1.0.0"
WINDOWED=1
ADHOC_SIGN=0
declare -a ADDDATA=()

function usage() {
  cat <<EOF
Build a macOS .app and .dmg from a Python project.

Required:
  -n, --name         App display name (e.g., "MyApp")
  -e, --entry        Entry point .py file (e.g., src/main.py)

Optional:
  -i, --icon         App icon (.icns or .png). If .png, will be converted.
  -o, --outdir       Output directory for DMG (default: dist)
  -b, --bundle-id    macOS bundle identifier (default: com.example.app)
  -v, --version      App version (default: 1.0.0)
      --no-windowed  Build as a console app (default: windowed)
      --add-data     Extra files (may repeat). Format: "SRC:DEST" (colon separator on macOS)
      --adhoc-sign   Ad-hoc codesign the .app (no notarization)
  -h, --help         Show this help

Examples:
  ./build_macos_app_dmg.sh -n "MyApp" -e app/main.py -i assets/icon.png -b com.me.myapp -v 1.2.3 --add-data "assets/:assets/"
  ./build_macos_app_dmg.sh -n "ConsoleTool" -e tool.py --no-windowed
EOF
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--name) APP_NAME="${2:-}"; shift 2;;
    -e|--entry) ENTRY_POINT="${2:-}"; shift 2;;
    -i|--icon) ICON_PATH="${2:-}"; shift 2;;
    -o|--outdir) OUTDIR="${2:-}"; shift 2;;
    -b|--bundle-id) BUNDLE_ID="${2:-}"; shift 2;;
    -v|--version) VERSION="${2:-}"; shift 2;;
    --no-windowed) WINDOWED=0; shift;;
    --add-data) ADDDATA+=("${2:-}"); shift 2;;
    --adhoc-sign) ADHOC_SIGN=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown argument: $1"; usage; exit 1;;
  esac
done

# Validate required
if [[ -z "$APP_NAME" || -z "$ENTRY_POINT" ]]; then
  echo "Error: --name and --entry are required."
  usage
  exit 1
fi

if [[ ! -f "$ENTRY_POINT" ]]; then
  echo "Error: entry point '$ENTRY_POINT' not found."
  exit 1
fi

# Check required tools
if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "Error: pyinstaller not found. Install with: python -m pip install pyinstaller"
  exit 1
fi

if ! command -v hdiutil >/dev/null 2>&1; then
  echo "Error: hdiutil not found. This script must run on macOS."
  exit 1
fi

# Prepare icon (.icns). If PNG supplied, convert to ICNS.
ICON_ICNS=""
cleanup_icon_tmp=""

function convert_png_to_icns() {
  local png="$1"
  local out_icns="$2"
  if ! command -v sips >/dev/null 2>&1; then
    echo "Error: 'sips' not found. Cannot convert PNG to ICNS. Install Xcode command line tools."
    exit 1
  fi
  if ! command -v iconutil >/dev/null 2>&1; then
    echo "Error: 'iconutil' not found. Cannot convert PNG to ICNS."
    exit 1
  fi

  local tmpdir
  tmpdir="$(mktemp -d)"
  cleanup_icon_tmp="$tmpdir"
  local iconset="$tmpdir/icon.iconset"
  mkdir -p "$iconset"

  # Generate required sizes
  # macOS iconset expects these pairs (non-retina and retina):
  # 16, 32, 64, 128, 256, 512 plus @2x variants
  for size in 16 32 64 128 256 512; do
    sips -z "$size" "$size" "$png" --out "$iconset/icon_${size}x${size}.png" >/dev/null
    sips -z $((size*2)) $((size*2)) "$png" --out "$iconset/icon_${size}x${size}@2x.png" >/dev/null
  done

  iconutil -c icns "$iconset" -o "$out_icns"
}

if [[ -n "$ICON_PATH" ]]; then
  case "$ICON_PATH" in
    *.icns)
      ICON_ICNS="$ICON_PATH"
      ;;
    *.png)
      ICON_ICNS="$(pwd)/${APP_NAME}.icns"
      echo "Converting PNG icon to ICNS..."
      convert_png_to_icns "$ICON_PATH" "$ICON_ICNS"
      ;;
    *)
      echo "Warning: icon must be .icns or .png. Ignoring '$ICON_PATH'."
      ICON_ICNS=""
      ;;
  esac
fi

# Build with PyInstaller
PYI_ARGS=(
  --name "$APP_NAME"
  --osx-bundle-identifier "$BUNDLE_ID"
  --noconfirm
)

PYI_ARGS+=(--collect-all pandas)
PYI_ARGS+=(--collect-all transliterate)
PYI_ARGS+=(--collect-all openpyxl)
PYI_ARGS+=(--exclude-module PyQt6.QtBluetooth)

if [[ $WINDOWED -eq 1 ]]; then
  PYI_ARGS+=(--windowed)
fi

if [[ -n "$ICON_ICNS" ]]; then
  PYI_ARGS+=(--icon "$ICON_ICNS")
fi

# Pass add-data entries
if [[ ${#ADDDATA[@]} -gt 0 ]]; then
  for dd in "${ADDDATA[@]}"; do
    PYI_ARGS+=(--add-data "$dd")
  done
fi

echo "Running PyInstaller..."
pyinstaller "${PYI_ARGS[@]}" "$ENTRY_POINT"

APP_PATH="dist/${APP_NAME}.app"
PLIST="$APP_PATH/Contents/Info.plist"

if [[ ! -d "$APP_PATH" ]]; then
  echo "Error: .app bundle not found at $APP_PATH"
  exit 1
fi

# Update Info.plist with version/display name
if [[ -f "$PLIST" ]]; then
  echo "Updating Info.plist..."
  /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $VERSION" "$PLIST"

  /usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION" "$PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $VERSION" "$PLIST"

  /usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName $APP_NAME" "$PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string $APP_NAME" "$PLIST"
fi

# Optionally ad-hoc sign
if [[ $ADHOC_SIGN -eq 1 ]]; then
  if command -v codesign >/dev/null 2>&1; then
    echo "Ad-hoc signing the app bundle..."
    codesign --deep --force -s - "$APP_PATH" || echo "Warning: codesign failed."
  else
    echo "Warning: codesign not found; skipping signing."
  fi
fi

# Create DMG
mkdir -p "$OUTDIR"
STAGING="$(mktemp -d)"
cp -R "$APP_PATH" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

DMG_PATH="$OUTDIR/${APP_NAME}-${VERSION}.dmg"
echo "Creating DMG at $DMG_PATH ..."
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGING" -ov -format UDZO "$DMG_PATH" >/dev/null

# Cleanup temp icon dir if created
if [[ -n "${cleanup_icon_tmp:-}" && -d "$cleanup_icon_tmp" ]]; then
  rm -rf "$cleanup_icon_tmp"
fi

echo ""
echo "✅ Done!"
echo "App: $APP_PATH"
echo "DMG: $DMG_PATH"
