#!/bin/bash
# build-deb.sh — Build .deb package for Debian/Ubuntu/SteamOS
set -euo pipefail

cd "$(dirname "$0")/../.."

VERSION=$(python3 -c "exec(open('steam_library_manager/version.py').read()); print(__version__)")
APP_ID="io.github.switch_bros.SteamLibraryManager"
PKG_NAME="steam-library-manager"
PKG_DIR="dist/deb-build/${PKG_NAME}_${VERSION}_all"

echo "Building .deb for SteamLibraryManager v${VERSION}..."

# Clean
rm -rf "dist/deb-build" "dist/${PKG_NAME}_${VERSION}_all.deb"
mkdir -p "${PKG_DIR}"

# Build wheel
python3 -m build --wheel --no-isolation

# Install application via python installer
python3 -m installer --destdir="${PKG_DIR}" dist/steam_library_manager-*.whl

# Bundle dependencies not available in Debian repos
# (vdf, steam, pywebview, requests-oauthlib, etc.)
SITE_PKG=$(python3 -c "import sysconfig; print(sysconfig.get_path('purelib'))")
DEST_SITE="${PKG_DIR}${SITE_PKG}"
mkdir -p "${DEST_SITE}"
pip install --target="${DEST_SITE}" \
    vdf steam pywebview requests-oauthlib qrcode pycryptodome packaging \
    --no-deps 2>/dev/null || true

# Desktop integration
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${PKG_DIR}/usr/share/icons/hicolor/512x512/apps"
mkdir -p "${PKG_DIR}/usr/share/metainfo"
mkdir -p "${PKG_DIR}/usr/share/licenses/${PKG_NAME}"

cp flatpak/${APP_ID}.desktop \
    "${PKG_DIR}/usr/share/applications/"
cp steam_library_manager/resources/icon.svg \
    "${PKG_DIR}/usr/share/icons/hicolor/scalable/apps/${APP_ID}.svg"
cp steam_library_manager/resources/icon.png \
    "${PKG_DIR}/usr/share/icons/hicolor/512x512/apps/${APP_ID}.png"
cp steam_library_manager/resources/${APP_ID}.metainfo.xml \
    "${PKG_DIR}/usr/share/metainfo/"
cp LICENSE "${PKG_DIR}/usr/share/licenses/${PKG_NAME}/"

# DEBIAN control files
mkdir -p "${PKG_DIR}/DEBIAN"

cat > "${PKG_DIR}/DEBIAN/control" << EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Section: games
Priority: optional
Architecture: all
Maintainer: SwitchBros <switchbros@proton.me>
Homepage: https://github.com/Switch-Bros/SteamLibraryManager
Description: A powerful Steam library organizer for Linux
 The modern Depressurizer alternative. Organize your Steam library with
 Smart Collections, AutoCat, Steam Deck optimization, achievement tracking,
 HLTB integration, and more. Supports 17 auto-categorization types,
 external game platforms, and full i18n (English/German).
Depends: python3 (>= 3.10),
 python3-pyqt6,
 python3-psutil,
 python3-pil,
 python3-yaml,
 python3-bs4,
 python3-lxml,
 python3-requests,
 python3-protobuf
Recommends: python3-keyring
EOF

# Post-install: update caches
cat > "${PKG_DIR}/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database /usr/share/applications 2>/dev/null || true
EOF
chmod 755 "${PKG_DIR}/DEBIAN/postinst"

# Post-remove: update caches
cat > "${PKG_DIR}/DEBIAN/postrm" << 'EOF'
#!/bin/sh
set -e
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database /usr/share/applications 2>/dev/null || true
EOF
chmod 755 "${PKG_DIR}/DEBIAN/postrm"

# Build .deb
dpkg-deb --build --root-owner-group "${PKG_DIR}"
mv "dist/deb-build/${PKG_NAME}_${VERSION}_all.deb" dist/

echo ""
echo "Created: dist/${PKG_NAME}_${VERSION}_all.deb"
echo "Size: $(du -h "dist/${PKG_NAME}_${VERSION}_all.deb" | cut -f1)"
echo ""
echo "Install with: sudo apt install ./dist/${PKG_NAME}_${VERSION}_all.deb"
