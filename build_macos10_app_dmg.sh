#!/usr/bin/env bash
# Build a macOS .app and .dmg from a Python project using PyInstaller.
# Usage:
#   ./build_macos_app_dmg.sh -n "MyApp" -e path/to/main.py -i assets/icon.png -b com.example.myapp -v 1.0.0 --add-data "data/:data/"
#
# Notes:
# - Requires macOS. Ensure Python 3 and PyInstaller are installed: python3 -m pip install pyinstaller
# - Icon can be .icns or .png (this script can convert PNG -> ICNS using sips + iconutil).
# - For --add-data, use the format 'SRC:DEST' (colon on macOS), e.g. "data/:data/".
# - The resulting .app lives under dist/, and a compressed DMG is created in the output directory (default: dist).
# - Optional: --adhoc-sign will ad-hoc sign the .app (basic signing).
# - Optional: --adhoc-sign-strong will thoroughly sign all nested binaries, frameworks, and bundles.
# - Adapted for compatibility with macOS 10.15.7 (Catalina): sets MACOSX_DEPLOYMENT_TARGET=10.15, targets x86_64 architecture, and sets LSMinimumSystemVersion in Info.plist.
# - If running on arm64, reruns the script under x86_64 via Rosetta for compatibility.

set -euo pipefail

# Run under x86_64 if on arm64
if [ "$(uname -m)" = "arm64" ]; then
  exec arch -x86_64 "$0" "$@"
fi

APP_NAME="PhraseTools"
ENTRY_POINT="main_merged_qt5.py"
ICON_PATH="ico.png"
OUTDIR="dist"
BUNDLE_ID="com.phrase_tools.app"
VERSION="1.0.0"
WINDOWED=1
ADHOC_SIGN=0
ADHOC_SIGN_STRONG=0
VERBOSE=0
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
      --adhoc-sign   Basic ad-hoc codesign the .app (no notarization)
      --adhoc-sign-strong  Thorough ad-hoc signing of all nested binaries, libraries, and frameworks
      --verbose      Enable verbose output
  -h, --help         Show this help

Examples:
  ./build_macos_app_dmg.sh -n "MyApp" -e app/main.py -i assets/icon.png -b com.me.myapp -v 1.2.3 --add-data "assets/:assets/"
  ./build_macos_app_dmg.sh -n "ConsoleTool" -e tool.py --no-windowed --adhoc-sign-strong
EOF
}

function log_info() {
  echo "ℹ️  $*"
}

function log_success() {
  echo "✅ $*"
}

function log_warning() {
  echo "⚠️  $*"
}

function log_error() {
  echo "❌ $*" >&2
}

function log_verbose() {
  if [[ $VERBOSE -eq 1 ]]; then
    echo "🔍 $*"
  fi
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
    --adhoc-sign-strong) ADHOC_SIGN_STRONG=1; shift;;
    --verbose) VERBOSE=1; shift;;
    -h|--help) usage; exit 0;;
    *) log_error "Unknown argument: $1"; usage; exit 1;;
  esac
done

# Validate required
if [[ -z "$APP_NAME" || -z "$ENTRY_POINT" ]]; then
  log_error "--name and --entry are required."
  usage
  exit 1
fi

if [[ ! -f "$ENTRY_POINT" ]]; then
  log_error "entry point '$ENTRY_POINT' not found."
  exit 1
fi

# Check required tools
if ! command -v pyinstaller >/dev/null 2>&1; then
  log_error "pyinstaller not found. Install with: python -m pip install pyinstaller"
  exit 1
fi

if ! command -v hdiutil >/dev/null 2>&1; then
  log_error "hdiutil not found. This script must run on macOS."
  exit 1
fi

# Prepare icon (.icns). If PNG supplied, convert to ICNS.
ICON_ICNS=""
cleanup_icon_tmp=""

function convert_png_to_icns() {
  local png="$1"
  local out_icns="$2"
  if ! command -v sips >/dev/null 2>&1; then
    log_error "'sips' not found. Cannot convert PNG to ICNS. Install Xcode command line tools."
    exit 1
  fi
  if ! command -v iconutil >/dev/null 2>&1; then
    log_error "'iconutil' not found. Cannot convert PNG to ICNS."
    exit 1
  fi

  local tmpdir
  tmpdir="$(mktemp -d)"
  cleanup_icon_tmp="$tmpdir"
  local iconset="$tmpdir/icon.iconset"
  mkdir -p "$iconset"

  log_info "Generating icon sizes from PNG..."
  # Generate required sizes
  # macOS iconset expects these pairs (non-retina and retina):
  # 16, 32, 64, 128, 256, 512 plus @2x variants
  for size in 16 32 64 128 256 512; do
    log_verbose "Creating ${size}x${size} icon variant"
    sips -z "$size" "$size" "$png" --out "$iconset/icon_${size}x${size}.png" >/dev/null
    sips -z $((size*2)) $((size*2)) "$png" --out "$iconset/icon_${size}x${size}@2x.png" >/dev/null
  done

  log_verbose "Converting iconset to ICNS format"
  iconutil -c icns "$iconset" -o "$out_icns"
  log_success "Icon converted to ICNS format"
}

if [[ -n "$ICON_PATH" ]]; then
  case "$ICON_PATH" in
    *.icns)
      ICON_ICNS="$ICON_PATH"
      log_info "Using ICNS icon: $ICON_ICNS"
      ;;
    *.png)
      ICON_ICNS="$(pwd)/${APP_NAME}.icns"
      log_info "Converting PNG icon to ICNS..."
      convert_png_to_icns "$ICON_PATH" "$ICON_ICNS"
      ;;
    *)
      log_warning "icon must be .icns or .png. Ignoring '$ICON_PATH'."
      ICON_ICNS=""
      ;;
  esac
fi

# Set deployment target for macOS 10.15 compatibility
export MACOSX_DEPLOYMENT_TARGET=10.15
log_info "Setting deployment target: macOS 10.15"

# Build with PyInstaller
PYI_ARGS=(
  --name "$APP_NAME"
  --osx-bundle-identifier "$BUNDLE_ID"
  --noconfirm
  --target-architecture x86_64  # Target Intel x86_64 for macOS 10.15 compatibility
)

PYI_ARGS+=(--collect-all pandas)
PYI_ARGS+=(--collect-all transliterate)
PYI_ARGS+=(--collect-all openpyxl)
#PYI_ARGS+=(--exclude-module PyQt6.QtBluetooth)

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

log_info "Running PyInstaller with MACOSX_DEPLOYMENT_TARGET=10.15 and x86_64 target..."
if [[ $VERBOSE -eq 1 ]]; then
  log_verbose "PyInstaller arguments: ${PYI_ARGS[*]}"
fi

pyinstaller "${PYI_ARGS[@]}" "$ENTRY_POINT"

APP_PATH="dist/${APP_NAME}.app"
PLIST="$APP_PATH/Contents/Info.plist"

if [[ ! -d "$APP_PATH" ]]; then
  log_error ".app bundle not found at $APP_PATH"
  exit 1
fi

log_success "PyInstaller completed successfully"

# Update Info.plist with version/display name and minimum system version
if [[ -f "$PLIST" ]]; then
  log_info "Updating Info.plist..."
  /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $VERSION" "$PLIST"

  /usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION" "$PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $VERSION" "$PLIST"

  /usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName $APP_NAME" "$PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string $APP_NAME" "$PLIST"

  /usr/libexec/PlistBuddy -c "Set :LSMinimumSystemVersion 10.15.0" "$PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string 10.15.0" "$PLIST"

  log_success "Info.plist updated"
fi

# Function for strong ad-hoc signing
function adhoc_sign_strong() {
  local app_path="$1"

  if ! command -v codesign >/dev/null 2>&1; then
    log_warning "codesign not found; skipping strong signing."
    return 1
  fi

  log_info "Performing thorough ad-hoc signing..."

  # Step 1: Sign all nested executables, .dylib and .so files
  log_info "Signing nested binaries and libraries..."
  local signed_count=0
  while IFS= read -r -d '' file; do
    log_verbose "Signing: $file"
    if codesign --force -s - "$file" 2>/dev/null; then
      ((signed_count++))
    else
      log_verbose "Failed to sign: $file"
    fi
  done < <(find "$app_path" -type f \( -perm +111 -o -name "*.dylib" -o -name "*.so" \) -print0 2>/dev/null)
  log_success "Signed $signed_count nested binaries and libraries"

  # Step 2: Sign Qt frameworks (if any exist)
  local frameworks_dir="$app_path/Contents/Frameworks"
  if [[ -d "$frameworks_dir" ]]; then
    log_info "Signing Qt frameworks..."
    local framework_count=0
    while IFS= read -r -d '' framework; do
      log_verbose "Signing framework: $framework"
      if codesign --force -s - "$framework" 2>/dev/null; then
        ((framework_count++))
      else
        log_verbose "Failed to sign framework: $framework"
      fi
    done < <(find "$frameworks_dir" -name "*.framework" -type d -print0 2>/dev/null)

    if [[ $framework_count -gt 0 ]]; then
      log_success "Signed $framework_count frameworks"
    else
      log_info "No frameworks found to sign"
    fi
  fi

  # Step 3: Final signature of the entire bundle
  log_info "Signing the main app bundle..."
  if codesign --deep --force -s - "$app_path"; then
    log_success "Main app bundle signed successfully"
  else
    log_warning "Failed to sign main app bundle"
    return 1
  fi

  # Step 4: Verify the signature
  log_info "Verifying signature..."
  if codesign --verify --deep --strict --verbose=2 "$app_path" 2>/dev/null; then
    log_success "Signature verification passed"
  else
    log_warning "Signature verification failed, but continuing..."
  fi

  return 0
}

# Function for basic ad-hoc signing
function adhoc_sign_basic() {
  local app_path="$1"

  if ! command -v codesign >/dev/null 2>&1; then
    log_warning "codesign not found; skipping signing."
    return 1
  fi

  log_info "Performing basic ad-hoc signing..."
  if codesign --deep --force -s - "$app_path"; then
    log_success "Basic ad-hoc signing completed"
    return 0
  else
    log_warning "Basic ad-hoc signing failed"
    return 1
  fi
}

# Apply signing based on options
if [[ $ADHOC_SIGN_STRONG -eq 1 ]]; then
  adhoc_sign_strong "$APP_PATH"
elif [[ $ADHOC_SIGN -eq 1 ]]; then
  adhoc_sign_basic "$APP_PATH"
fi

# Create DMG
log_info "Creating DMG package..."
mkdir -p "$OUTDIR"
STAGING="$(mktemp -d)"
cp -R "$APP_PATH" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

DMG_PATH="$OUTDIR/${APP_NAME}-${VERSION}.dmg"
log_verbose "DMG will be created at: $DMG_PATH"

if hdiutil create -volname "$APP_NAME" -srcfolder "$STAGING" -ov -format UDZO "$DMG_PATH" >/dev/null 2>&1; then
  log_success "DMG created successfully"
else
  log_error "Failed to create DMG"
  exit 1
fi

# Cleanup temp icon dir if created
if [[ -n "${cleanup_icon_tmp:-}" && -d "$cleanup_icon_tmp" ]]; then
  rm -rf "$cleanup_icon_tmp"
  log_verbose "Cleaned up temporary icon files"
fi

# Cleanup staging dir
if [[ -d "$STAGING" ]]; then
  rm -rf "$STAGING"
  log_verbose "Cleaned up staging directory"
fi

# Final summary
echo ""
log_success "Build completed successfully!"
echo ""
echo "📱 App Bundle: $APP_PATH"
echo "💾 DMG Package: $DMG_PATH"
echo ""

# Display app info
if [[ -f "$PLIST" ]]; then
  echo "App Information:"
  echo "  Name: $APP_NAME"
  echo "  Version: $VERSION"
  echo "  Bundle ID: $BUNDLE_ID"
  echo "  Min macOS: 10.15.0"
  echo "  Architecture: x86_64"

  if [[ $ADHOC_SIGN_STRONG -eq 1 ]]; then
    echo "  Code Signing: Strong ad-hoc"
  elif [[ $ADHOC_SIGN -eq 1 ]]; then
    echo "  Code Signing: Basic ad-hoc"
  else
    echo "  Code Signing: None"
  fi
fi

# Show DMG size
if [[ -f "$DMG_PATH" ]]; then
  DMG_SIZE=$(du -h "$DMG_PATH" | cut -f1)
  echo "  DMG Size: $DMG_SIZE"
fi

echo ""
log_info "Ready for distribution on macOS 10.15+ (Intel/Rosetta)"