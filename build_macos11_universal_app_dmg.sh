#!/usr/bin/env bash
# Build macOS 11+ Universal (.app + .dmg) from a Python project using PyInstaller.
# Supports separate-arch builds in different environments and a later merge step.
#
# Modes:
#   --mode x64      -> build only x86_64 app (+ optional dmg)
#   --mode arm64    -> build only arm64 app (+ optional dmg)
#   --mode both     -> build x86_64 and arm64 on the same machine, then merge and dmg
#   --mode merge    -> merge given x86_64 and arm64 .app into Universal2 and create dmg
#
# Example (separate environments workflow):
#   # On Intel/x86_64 machine:
#   ./build_macos11_universal_app_dmg.sh --mode x64 -n "MyApp" -e app/main.py -i icon.png -b com.me.myapp -v 1.2.3 --add-data "assets/:assets/"
#   # This produces dist_x64/MyApp.app (and optionally dist_x64/MyApp-1.2.3-x64.dmg if --make-dmg)
#
#   # On Apple Silicon/arm64 machine:
#   ./build_macos11_universal_app_dmg.sh --mode arm64 -n "MyApp" -e app/main.py -i icon.png -b com.me.myapp -v 1.2.3 --add-data "assets/:assets/"
#   # This produces dist_arm64/MyApp.app (and optionally dist_arm64/MyApp-1.2.3-arm64.dmg if --make-dmg)
#
#   # Merge (run on any macOS 11+ machine with lipo installed):
#   ./build_macos11_universal_app_dmg.sh --mode merge -n "MyApp" -b com.me.myapp -v 1.2.3 \
#       --x64-app /path/to/dist_x64/MyApp.app \
#       --arm64-app /path/to/dist_arm64/MyApp.app \
#       --adhoc-sign-strong
#
# Notes:
# - Requires macOS 11+ with Python 3, PyInstaller for build modes, Xcode CLTs (for lipo, sips, iconutil, PlistBuddy).
# - PyInstaller must be >= 5.10 for stable --target-architecture support.
# - For --add-data on macOS, use colon separator: 'SRC:DEST'.
# - Output directories:
#     dist_x64/       -> x86_64 .app (+ optional dmg)
#     dist_arm64/     -> arm64 .app (+ optional dmg)
#     dist_universal/ -> merged Universal .app and final .dmg
#
set -euo pipefail

MODE="both" # x64|arm64|both|merge
APP_NAME="PhraseTools"
ENTRY_POINT="main_merged_qt5.py"
ICON_PATH="icon_1.png"
BUNDLE_ID="com.phrase_tools.app"
VERSION="1.0.0"
WINDOWED=1
ADHOC_SIGN=0
ADHOC_SIGN_STRONG=0
VERBOSE=0
MAKE_DMG=1

# For merge mode, allow explicit .app inputs:
MERGE_X64_APP=""
MERGE_ARM64_APP=""

declare -a ADDDATA=()

OUTDIR_X64="dist_x64"
OUTDIR_ARM64="dist_arm64"
OUTDIR_UNIV="dist_universal"

function usage() {
  cat <<EOF
Build macOS 11+ apps (x86_64/arm64), merge into Universal2, and make .dmg

Required (for build modes x64/arm64/both):
  -n, --name         App display name (e.g., "MyApp")
  -e, --entry        Entry point .py file (e.g., src/main.py)

Required (for --mode merge):
  -n, --name         App display name (used for output naming)
  --x64-app          Path to the x86_64 .app
  --arm64-app        Path to the arm64 .app

Optional:
  -i, --icon         App icon (.icns or .png). If .png, will be converted (build modes only).
  -b, --bundle-id    macOS bundle identifier (default: com.example.app)
  -v, --version      App version (default: 1.0.0)
      --no-windowed  Build as a console app (default: windowed)
      --add-data     Extra files (repeatable). Format: "SRC:DEST" (colon separator on macOS)
      --adhoc-sign   Basic ad-hoc codesign the resulting .app (no notarization)
      --adhoc-sign-strong  Thorough ad-hoc signing of nested binaries/frameworks
      --no-dmg       Do not create .dmg (default: creates dmg for target of the mode)
      --mode         x64 | arm64 | both | merge
      --x64-app      Path to prebuilt x86_64 .app (merge mode)
      --arm64-app    Path to prebuilt arm64 .app (merge mode)
      --verbose      Verbose output
  -h, --help         Show this help
EOF
}

function log_info()  { echo "ℹ️  $*"; }
function log_success(){ echo "✅ $*"; }
function log_warning(){ echo "⚠️  $*"; }
function log_error() { echo "❌ $*" >&2; }
function log_verbose(){
  if [[ $VERBOSE -eq 1 ]]; then
    echo "🔍 $*"
  fi
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2;;
    -n|--name) APP_NAME="${2:-}"; shift 2;;
    -e|--entry) ENTRY_POINT="${2:-}"; shift 2;;
    -i|--icon) ICON_PATH="${2:-}"; shift 2;;
    -b|--bundle-id) BUNDLE_ID="${2:-}"; shift 2;;
    -v|--version) VERSION="${2:-}"; shift 2;;
    --no-windowed) WINDOWED=0; shift;;
    --add-data) ADDDATA+=("${2:-}"); shift 2;;
    --adhoc-sign) ADHOC_SIGN=1; shift;;
    --adhoc-sign-strong) ADHOC_SIGN_STRONG=1; shift;;
    --no-dmg) MAKE_DMG=0; shift;;
    --x64-app) MERGE_X64_APP="${2:-}"; shift 2;;
    --arm64-app) MERGE_ARM64_APP="${2:-}"; shift 2;;
    --verbose) VERBOSE=1; shift;;
    -h|--help) usage; exit 0;;
    *) log_error "Unknown argument: $1"; usage; exit 1;;
  esac
done

# Normalize mode
case "$MODE" in
  x64|arm64|both|merge) ;;
  *) log_error "--mode must be one of: x64, arm64, both, merge"; exit 1;;
esac

# Tooling checks depending on mode
function require_tools() {
  for tool in "$@"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      log_error "Required tool '$tool' not found."
      exit 1
    fi
  done
}

if [[ "$MODE" == "merge" ]]; then
  require_tools lipo hdiutil
else
  require_tools python3 pyinstaller hdiutil lipo
fi

# Validate required based on mode
if [[ "$MODE" == "merge" ]]; then
  if [[ -z "${APP_NAME:-}" ]]; then
    log_error "--name is required for merge mode (for output naming)."; exit 1;
  fi
  if [[ -z "${MERGE_X64_APP:-}" || -z "${MERGE_ARM64_APP:-}" ]]; then
    log_error "For --mode merge you must provide --x64-app and --arm64-app paths."; exit 1;
  fi
  if [[ ! -d "$MERGE_X64_APP" ]]; then log_error "x64 app not found: $MERGE_X64_APP"; exit 1; fi
  if [[ ! -d "$MERGE_ARM64_APP" ]]; then log_error "arm64 app not found: $MERGE_ARM64_APP"; exit 1; fi
else
  if [[ -z "${APP_NAME:-}" || -z "${ENTRY_POINT:-}" ]]; then
    log_error "--name and --entry are required for build modes."; usage; exit 1;
  fi
  if [[ ! -f "$ENTRY_POINT" ]]; then
    log_error "Entry point '$ENTRY_POINT' not found."; exit 1;
  fi
fi

# Icon handling (build modes only). If PNG supplied, convert to ICNS.
ICON_ICNS=""
cleanup_icon_tmp=""

function convert_png_to_icns() {
  local png="$1"
  local out_icns="$2"
  for t in sips iconutil; do
    if ! command -v "$t" >/dev/null 2>&1; then
      log_error "'$t' not found. Cannot convert PNG to ICNS. Install Xcode Command Line Tools."
      exit 1
    fi
  done

  local tmpdir
  tmpdir="$(mktemp -d)"
  cleanup_icon_tmp="$tmpdir"
  local iconset="$tmpdir/icon.iconset"
  mkdir -p "$iconset"

  log_info "Generating icon sizes from PNG..."
  for size in 16 32 64 128 256 512; do
    log_verbose "Creating ${size}x${size} and @2x"
    sips -z "$size" "$size" "$png" --out "$iconset/icon_${size}x${size}.png" >/dev/null
    sips -z $((size*2)) $((size*2)) "$png" --out "$iconset/icon_${size}x${size}@2x.png" >/dev/null
  done
  iconutil -c icns "$iconset" -o "$out_icns"
  log_success "Icon converted to ICNS: $out_icns"
}

if [[ "$MODE" != "merge" ]]; then
  if [[ -n "${ICON_PATH:-}" ]]; then
    case "$ICON_PATH" in
      *.icns) ICON_ICNS="$ICON_PATH"; log_info "Using ICNS icon: $ICON_ICNS";;
      *.png)  ICON_ICNS="$(pwd)/${APP_NAME}.icns"; log_info "Converting PNG icon to ICNS..."; convert_png_to_icns "$ICON_PATH" "$ICON_ICNS";;
      *)      log_warning "Icon must be .icns or .png. Ignoring '$ICON_PATH'."; ICON_ICNS="";;
    esac
  fi
fi

# macOS 11+ target for all builds
export MACOSX_DEPLOYMENT_TARGET=11.0
log_info "Setting deployment target: macOS 11.0"
log_info "Selected mode: $MODE"
if [[ $VERBOSE -eq 1 ]]; then set -x; fi

# Common PyInstaller args
PYI_COMMON=(
  --name "$APP_NAME"
  --osx-bundle-identifier "$BUNDLE_ID"
  --noconfirm
)

# Collects for common libs (adjust as needed)
PYI_COMMON+=(--collect-all pandas)
PYI_COMMON+=(--collect-all transliterate)
PYI_COMMON+=(--collect-all openpyxl)

if [[ "$MODE" != "merge" && $WINDOWED -eq 1 ]]; then
  PYI_COMMON+=(--windowed)
fi
if [[ "$MODE" != "merge" && -n "$ICON_ICNS" ]]; then
  PYI_COMMON+=(--icon "$ICON_ICNS")
fi
# Add data
if [[ "$MODE" != "merge" && ${#ADDDATA[@]} -gt 0 ]]; then
  for dd in "${ADDDATA[@]}"; do
    PYI_COMMON+=(--add-data "$dd")
  done
fi

# Info.plist updater
function plist_set_common() {
  local plist="$1"
  /usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" "$plist" 2>/dev/null || /usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $VERSION" "$plist"
  /usr/libexec/PlistBuddy -c "Set :CFBundleVersion $VERSION" "$plist" 2>/dev/null || /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $VERSION" "$plist"
  /usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName $APP_NAME" "$plist" 2>/dev/null || /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string $APP_NAME" "$plist"
  /usr/libexec/PlistBuddy -c "Set :LSMinimumSystemVersion 11.0.0" "$plist" 2>/dev/null || /usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string 11.0.0" "$plist"
}

# Build helpers
function build_arch() {
  local arch="$1" # x86_64 or arm64
  local outdir="$2"
  log_info "Building $arch app with PyInstaller..."
  rm -rf "$outdir" && mkdir -p "$outdir"
  pyinstaller "${PYI_COMMON[@]}" --target-architecture "$arch" "$ENTRY_POINT"

  if [[ -d "dist/${APP_NAME}.app" ]]; then
    mv -f "dist/${APP_NAME}.app" "$outdir/${APP_NAME}.app"
  fi
  local app_path="$outdir/${APP_NAME}.app"
  [[ -d "$app_path" ]] || { log_error ".app ($arch) not found at $app_path"; exit 1; }
  local plist="$app_path/Contents/Info.plist"
  if [[ -f "$plist" ]]; then plist_set_common "$plist"; fi
  log_success "$arch build complete: $app_path"

  if [[ $MAKE_DMG -eq 1 ]]; then
    make_dmg "$app_path" "${APP_NAME}-${VERSION}-${arch}.dmg" "$outdir"
  fi
}

function lipo_merge_file() {
  local x="$1"; local a="$2"; local dest="$3"
  if [[ -f "$x" && -f "$a" ]]; then
    lipo -create "$x" "$a" -output "$dest" >/dev/null 2>&1 || {
      log_warning "lipo failed for: $dest — copying x86_64 version"
      cp -f "$x" "$dest"
    }
  elif [[ -f "$x" ]]; then
    cp -f "$x" "$dest"
  elif [[ -f "$a" ]]; then
    cp -f "$a" "$dest"
  fi
}

function adhoc_sign_strong() {
  local app_path="$1"
  if ! command -v codesign >/dev/null 2>&1; then
    log_warning "codesign not found; skipping strong signing."
    return 1
  fi

  log_info "Thorough ad-hoc signing (nested binaries, frameworks, bundle)..."
  local signed_count=0
  while IFS= read -r -d '' file; do
    if file -b "$file" | grep -q "Mach-O"; then
      if codesign --force -s - "$file" 2>/dev/null; then
        ((signed_count++))
      fi
    fi
  done < <(find "$app_path" -type f \( -perm -111 -o -name "*.dylib" -o -name "*.so" \) -print0 2>/dev/null)
  log_success "Signed $signed_count nested binaries"

  local frameworks_dir="$app_path/Contents/Frameworks"
  if [[ -d "$frameworks_dir" ]]; then
    local framework_count=0
    while IFS= read -r -d '' framework; do
      if codesign --force -s - "$framework" 2>/dev/null; then
        ((framework_count++))
      fi
    done < <(find "$frameworks_dir" -name "*.framework" -type d -print0 2>/dev/null)
    log_info "Signed $framework_count frameworks"
  fi

  log_info "Signing the main app bundle..."
  if codesign --deep --force -s - "$app_path"; then
    log_success "Main app bundle signed"
  else
    log_warning "Failed to sign main app bundle"
  fi

  log_info "Verifying signature..."
  if codesign --verify --deep --strict --verbose=2 "$app_path" 2>/dev/null; then
    log_success "Signature verification passed"
  else
    log_warning "Signature verification failed (continuing)"
  fi
}

function adhoc_sign_basic() {
  local app_path="$1"
  if ! command -v codesign >/dev/null 2>&1; then
    log_warning "codesign not found; skipping signing."
    return 1
  fi
  log_info "Basic ad-hoc signing..."
  if codesign --deep --force -s - "$app_path"; then
    log_success "Basic ad-hoc signing completed"
  else
    log_warning "Basic ad-hoc signing failed"
  fi
}

function maybe_sign() {
  local app_path="$1"
  if [[ $ADHOC_SIGN_STRONG -eq 1 ]]; then
    adhoc_sign_strong "$app_path"
  elif [[ $ADHOC_SIGN -eq 1 ]]; then
    adhoc_sign_basic "$app_path"
  fi
}

function make_dmg() {
  local app_path="$1"
  local dmg_name="$2"
  local outdir="$3"
  log_info "Creating DMG: $dmg_name"
  mkdir -p "$outdir"
  local staging
  staging="$(mktemp -d)"
  cp -R "$app_path" "$staging/"
  ln -s /Applications "$staging/Applications"
  local dmg_path="$outdir/$dmg_name"
  if hdiutil create -volname "$APP_NAME" -srcfolder "$staging" -ov -format UDZO "$dmg_path" >/dev/null 2>&1; then
    log_success "DMG created: $dmg_path"
  else
    log_error "Failed to create DMG: $dmg_name"
    exit 1
  fi
  rm -rf "$staging"
}

# Merge two .apps into Universal
function merge_apps() {
  local app_x64="$1"
  local app_arm64="$2"
  local outdir="$OUTDIR_UNIV"
  rm -rf "$outdir" && mkdir -p "$outdir"
  local univ_app="$outdir/${APP_NAME}.app"

  log_info "Merging into Universal app..."
  cp -R "$app_x64" "$univ_app"

  # Lipo merge executables/libs/so files
  while IFS= read -r -d '' f; do
    rel="${f#"${univ_app}/"}"
    local fx="$app_x64/$rel"
    local fa="$app_arm64/$rel"
    if file -b "$fx" 2>/dev/null | grep -q "Mach-O"; then
      lipo_merge_file "$fx" "$fa" "$f"
    fi
  done < <(find "$univ_app" -type f \( -perm -111 -o -name "*.dylib" -o -name "*.so" \) -print0)

  # Frameworks (some exist only in one build)
  local frame_dir="$univ_app/Contents/Frameworks"
  if [[ -d "$frame_dir" ]]; then
    # Traverse both Frameworks trees without using GNU sort -z (not available on macOS by default)
    while IFS= read -r -d '' part; do
      rel="${part#"${app_x64}/"}"
      rel="${rel#"${app_arm64}/"}"
      # Map to relative path inside each app if it belongs to one of them
      if [[ "$part" == "$app_x64/"* ]]; then
        rel="${part#"${app_x64}/"}"
      elif [[ "$part" == "$app_arm64/"* ]]; then
        rel="${part#"${app_arm64}/"}"
      fi
      local fx="$app_x64/$rel"
      local fa="$app_arm64/$rel"
      if [[ -f "$fx" || -f "$fa" ]]; then
        mkdir -p "$(dirname "$univ_app/$rel")"
        lipo_merge_file "$fx" "$fa" "$univ_app/$rel"
      fi
    done < <( \
      { find "$app_x64/Contents/Frameworks" -type f -print0 2>/dev/null; } ; \
      { find "$app_arm64/Contents/Frameworks" -type f -print0 2>/dev/null; } \
    )
  fi

  local plist="$univ_app/Contents/Info.plist"
  if [[ -f "$plist" ]]; then plist_set_common "$plist"; fi

  log_success "Universal app created at: $univ_app"
  maybe_sign "$univ_app"

  if [[ $MAKE_DMG -eq 1 ]]; then
    make_dmg "$univ_app" "${APP_NAME}-${VERSION}-universal.dmg" "$outdir"
  fi
}

# Main flow
if [[ "$MODE" == "merge" ]]; then
  merge_apps "$MERGE_X64_APP" "$MERGE_ARM64_APP"
  exit 0
fi

# Build-only modes
if [[ "$MODE" == "x64" ]]; then
  build_arch "x86_64" "$OUTDIR_X64"
  exit 0
elif [[ "$MODE" == "arm64" ]]; then
  build_arch "arm64" "$OUTDIR_ARM64"
  exit 0
elif [[ "$MODE" == "both" ]]; then
  build_arch "x86_64" "$OUTDIR_X64"
  build_arch "arm64" "$OUTDIR_ARM64"
  merge_apps "$OUTDIR_X64/${APP_NAME}.app" "$OUTDIR_ARM64/${APP_NAME}.app"
  exit 0
fi

