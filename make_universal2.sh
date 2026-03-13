#!/usr/bin/env bash
# make_universal2.sh
# Create a universal2 (.app) by gluing arm64 and x86_64 builds, optionally create a DMG,
# and (optionally) sign ad-hoc or with Developer ID, and notarize/staple.
#
# Usage:
#   ./make_universal2.sh \
#     --x64 dist_x64/MyApp.app \
#     --arm dist_arm/MyApp.app \
#     --out dist_universal/MyApp.app \
#     [--dmg-out dist_universal/MyApp-1.0.0.dmg --volname "MyApp"] \
#     [--adhoc-sign-strong | --sign-id "Developer ID Application: Name (TEAMID)" --entitlements entitlements.plist] \
#     [--notary-profile AC_PROFILE --staple]
#
set -euo pipefail

X64_APP=""
ARM_APP=""
OUT_APP=""
DMG_OUT=""
VOLNAME=""

ADHOC_SIGN_STRONG=0
SIGN_ID=""
ENTITLEMENTS=""
NOTARY_PROFILE=""
STAPLE=0

usage() {
  cat <<EOF
Glue x86_64 and arm64 .app bundles into one universal2 .app, optionally create DMG and notarize.

Required:
  --x64 PATH       Path to x86_64 .app
  --arm PATH       Path to arm64  .app
  --out PATH       Output universal .app path (will be created)

Optional disk image:
  --dmg-out PATH   Create a DMG at this path (e.g., dist_universal/MyApp-1.0.0.dmg)
  --volname NAME   Volume name inside the DMG (defaults to app name)

Optional signing:
  --adhoc-sign-strong
  --sign-id "Developer ID Application: Name (TEAMID)"
  --entitlements path/to/entitlements.plist

Optional notarization:
  --notary-profile AC_PROFILE
  --staple

Examples:
  ./make_universal2.sh --x64 dist_x64/MyApp.app --arm dist_arm/MyApp.app --out dist_universal/MyApp.app \
      --dmg-out dist_universal/MyApp-1.0.0.dmg --volname "MyApp" --adhoc-sign-strong
  ./make_universal2.sh --x64 dist_x64/MyApp.app --arm dist_arm/MyApp.app --out dist_universal/MyApp.app \
      --dmg-out dist_universal/MyApp-1.0.0.dmg --volname "MyApp" \
      --sign-id "Developer ID Application: John Doe (TEAMID)" --entitlements entitlements.plist \
      --notary-profile AC_PROFILE --staple
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --x64) X64_APP="${2:-}"; shift 2;;
    --arm) ARM_APP="${2:-}"; shift 2;;
    --out) OUT_APP="${2:-}"; shift 2;;
    --dmg-out) DMG_OUT="${2:-}"; shift 2;;
    --volname) VOLNAME="${2:-}"; shift 2;;
    --adhoc-sign-strong) ADHOC_SIGN_STRONG=1; shift;;
    --sign-id) SIGN_ID="${2:-}"; shift 2;;
    --entitlements) ENTITLEMENTS="${2:-}"; shift 2;;
    --notary-profile) NOTARY_PROFILE="${2:-}"; shift 2;;
    --staple) STAPLE=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

[[ -d "$X64_APP" && -d "$ARM_APP" ]] || { echo "Error: --x64 and --arm must be existing .app bundles"; exit 1; }
[[ -n "$OUT_APP" ]] || { echo "Error: --out required"; exit 1; }

rm -rf "$OUT_APP"
mkdir -p "$(dirname "$OUT_APP")"
cp -R "$X64_APP" "$OUT_APP"

# Helper: lipo two files into OUT path
lipo_merge() {
  local f_rel="$1"
  local f_x64="$X64_APP/$f_rel"
  local f_arm="$ARM_APP/$f_rel"
  local f_out="$OUT_APP/$f_rel"

  if [[ -f "$f_x64" && -f "$f_arm" ]]; then
    if file "$f_x64" | grep -q "Mach-O"; then
      mkdir -p "$(dirname "$f_out")"
      lipo -create "$f_x64" "$f_arm" -output "$f_out"
      echo "merged: $f_rel"
    fi
  fi
}

# Detect main executable
MAIN_BASENAME="$(basename "$X64_APP" .app)"
MAIN_REL="Contents/MacOS/$MAIN_BASENAME"
if [[ ! -f "$OUT_APP/$MAIN_REL" ]]; then
  MAIN_REL="$(cd "$OUT_APP/Contents/MacOS" && ls -1 | head -n1)"
  MAIN_REL="Contents/MacOS/$MAIN_REL"
fi
lipo_merge "$MAIN_REL"

# Merge .dylib / .so
while IFS= read -r -d '' f; do
  rel="${f#"$X64_APP/"}"
  lipo_merge "$rel"
done < <(find "$X64_APP" -type f \( -name "*.dylib" -o -name "*.so" \) -print0)

# Framework inner binaries
while IFS= read -r -d '' fwbin; do
  rel="${fwbin#"$X64_APP/"}"
  lipo_merge "$rel"
done < <(find "$X64_APP/Contents/Frameworks" -type f -path "*/Versions/*/*" -print0 2>/dev/null || true)

# Plugins .dylib
while IFS= read -r -d '' plug; do
  rel="${plug#"$X64_APP/"}"
  lipo_merge "$rel"
done < <(find "$X64_APP/Contents/PlugIns" -type f -name "*.dylib" -print0 2>/dev/null || true)

echo "Verifying architectures (main executable):"
file "$OUT_APP/$MAIN_REL" || true
echo "Architectures list under Contents/MacOS:"
file "$OUT_APP/Contents/MacOS/"* || true

# Signing helpers
sign_all_inner() {
  local bundle="$1"; local ident="$2"
  find "$bundle" -type f \( -perm -111 -o -name "*.dylib" -o -name "*.so" \) -print0 \
    | xargs -0 -I{} codesign --force --sign "${ident:--}" "{}"
  if [[ -d "$bundle/Contents/Frameworks" ]]; then
    find "$bundle/Contents/Frameworks" -name "*.framework" -type d -print0 \
      | xargs -0 -I{} codesign --force --sign "${ident:--}" "{}"
  fi
}

# Sign
if [[ -n "$SIGN_ID" ]]; then
  echo "Developer ID signing universal app..."
  sign_all_inner "$OUT_APP" "$SIGN_ID"
  if [[ -n "$ENTITLEMENTS" ]]; then
    codesign --deep --force --options runtime --entitlements "$ENTITLEMENTS" --sign "$SIGN_ID" "$OUT_APP"
  else
    codesign --deep --force --options runtime --sign "$SIGN_ID" "$OUT_APP"
  fi
elif [[ $ADHOC_SIGN_STRONG -eq 1 ]]; then
  echo "Strong ad-hoc signing universal app..."
  sign_all_inner "$OUT_APP" ""
  codesign --deep --force -s - "$OUT_APP"
fi

echo "Verifying codesign..."
codesign --verify --deep --strict --verbose=2 "$OUT_APP" || echo "codesign verification reported issues."
spctl --assess --type execute --verbose=4 "$OUT_APP" || true

# Create DMG if requested
if [[ -n "$DMG_OUT" ]]; then
  [[ -n "$VOLNAME" ]] || VOLNAME="$MAIN_BASENAME"
  mkdir -p "$(dirname "$DMG_OUT")"
  STAGE="$(mktemp -d)"
  cp -R "$OUT_APP" "$STAGE/"
  ln -s /Applications "$STAGE/Applications"
  echo "Creating DMG at $DMG_OUT ..."
  hdiutil create -volname "$VOLNAME" -srcfolder "$STAGE" -ov -format UDZO "$DMG_OUT" >/dev/null

  # Notarization (if requested)
  if [[ -n "$NOTARY_PROFILE" ]]; then
    echo "Submitting for notarization (profile: $NOTARY_PROFILE)..."
    xcrun notarytool submit "$OUT_APP" --keychain-profile "$NOTARY_PROFILE" --wait
    if [[ ${STAPLE:-0} -eq 1 ]]; then
      xcrun stapler staple "$OUT_APP" || true
      xcrun stapler staple "$DMG_OUT" || true
    fi
  fi
fi

echo "✅ Done. Universal app: $OUT_APP"
if [[ -n "$DMG_OUT" ]]; then
  echo "DMG: $DMG_OUT"
fi
