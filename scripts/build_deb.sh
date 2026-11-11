#!/bin/bash
set -euo pipefail

# Build standalone Debian .deb package
PKG_NAME="ev-battery-soh"
VERSION="0.3.0"
ARCH="all"
BUILD_DIR="dist/deb/${PKG_NAME}_${VERSION}_${ARCH}"

echo "🔨 Building Debian package ${PKG_NAME}_${VERSION}_${ARCH}.deb..."

rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/lib/python3/dist-packages/ev_battery_soh"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/share/metainfo"
mkdir -p "${BUILD_DIR}/usr/share/doc/${PKG_NAME}"

# Control file
cat <<EOF > "${BUILD_DIR}/DEBIAN/control"
Package: ${PKG_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: python3, python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1, python3-pandas, python3-numpy, python3-scipy, python3-reportlab, python3-cryptography, python3-qrcode, python3-jinja2
Maintainer: Pierre Roth <pierre.roth@gmail.com>
Description: Electric Vehicle Battery State of Health Analyzer & Certifier
 Advanced telemetric battery capacity and State of Health (SOH) analyzer for electric vehicles.
 Includes CLI tool, native GNOME GTK4 Libadwaita desktop application, and official signed PDF certificate generator.
EOF

# Copy application python modules
cp *.py "${BUILD_DIR}/usr/lib/python3/dist-packages/ev_battery_soh/"
if [ -d templates ]; then
  cp -r templates "${BUILD_DIR}/usr/lib/python3/dist-packages/ev_battery_soh/"
fi

# Create executable wrappers in /usr/bin
cat <<'EOF' > "${BUILD_DIR}/usr/bin/ev-battery-soh"
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/lib/python3/dist-packages/ev_battery_soh")
from main import main
if __name__ == "__main__":
    sys.exit(main())
EOF
chmod 755 "${BUILD_DIR}/usr/bin/ev-battery-soh"

cat <<'EOF' > "${BUILD_DIR}/usr/bin/ev-battery-soh-gui"
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/lib/python3/dist-packages/ev_battery_soh")
from gnome_app import main
if __name__ == "__main__":
    sys.exit(main())
EOF
chmod 755 "${BUILD_DIR}/usr/bin/ev-battery-soh-gui"

# Install desktop file & metainfo
cp org.smilebob.EvBatterySoh.desktop "${BUILD_DIR}/usr/share/applications/"
cp data/org.smilebob.EvBatterySoh.metainfo.xml "${BUILD_DIR}/usr/share/metainfo/"

# Install icons
for s in 16 24 32 48 64 128 256 512; do
  mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/${s}x${s}/apps"
  cp "data/icons/${s}x${s}/org.smilebob.EvBatterySoh.png" "${BUILD_DIR}/usr/share/icons/hicolor/${s}x${s}/apps/"
done
mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps"
cp data/icons/org.smilebob.EvBatterySoh.svg "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps/"

# Install docs & copyright
cp LICENSE "${BUILD_DIR}/usr/share/doc/${PKG_NAME}/copyright"
cp README.md "${BUILD_DIR}/usr/share/doc/${PKG_NAME}/"

# Build deb package
dpkg-deb --build --root-owner-group "${BUILD_DIR}" "dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"

echo "✅ Package built: dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"
ls -lh "dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"
