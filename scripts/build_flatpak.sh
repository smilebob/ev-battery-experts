#!/bin/bash
set -euo pipefail

# Build standalone Flatpak bundle
APP_ID="org.smilebob.EvBatterySoh"
REPO_DIR="dist/flatpak/repo"
BUILD_DIR="dist/flatpak/build"
BUNDLE="dist/${APP_ID}.flatpak"

echo "🔨 Building Flatpak bundle ${BUNDLE}..."

mkdir -p dist/flatpak

flatpak-builder --force-clean \
  --repo="${REPO_DIR}" \
  "${BUILD_DIR}" \
  flatpak/org.smilebob.EvBatterySoh.yml

flatpak build-bundle "${REPO_DIR}" "${BUNDLE}" "${APP_ID}"

echo "✅ Flatpak bundle built: ${BUNDLE}"
ls -lh "${BUNDLE}"
