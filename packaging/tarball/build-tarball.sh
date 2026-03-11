#!/bin/bash
# build-tarball.sh — Build portable tar.gz distribution
set -euo pipefail

cd "$(dirname "$0")/../.."

VERSION=$(python3 -c "exec(open('steam_library_manager/version.py').read()); print(__version__)")
APP_ID="io.github.switch_bros.SteamLibraryManager"
DIST_NAME="SteamLibraryManager-${VERSION}-linux-x86_64"
DIST_DIR="dist/${DIST_NAME}"

echo "Building tar.gz for SteamLibraryManager v${VERSION}..."

# Clean
rm -rf "${DIST_DIR}" "dist/${DIST_NAME}.tar.gz"

# Build wheel
python3 -m build --wheel --no-isolation

# Create directory structure
mkdir -p "${DIST_DIR}"/{bin,lib,share/{applications,icons/hicolor/scalable/apps,metainfo}}

# Install wheel + dependencies into lib/
pip install --target="${DIST_DIR}/lib" dist/steam_library_manager-*.whl --no-deps
pip install --target="${DIST_DIR}/lib" -r requirements-user.txt

# Create launcher script
cat > "${DIST_DIR}/bin/steam-library-manager" << 'LAUNCHER'
#!/bin/bash
# Steam Library Manager launcher
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/lib:${PYTHONPATH:-}"
exec python3 -m steam_library_manager.main "$@"
LAUNCHER
chmod +x "${DIST_DIR}/bin/steam-library-manager"

# Desktop integration files
cp flatpak/${APP_ID}.desktop "${DIST_DIR}/share/applications/"
cp steam_library_manager/resources/icon.svg \
    "${DIST_DIR}/share/icons/hicolor/scalable/apps/${APP_ID}.svg"
cp steam_library_manager/resources/${APP_ID}.metainfo.xml \
    "${DIST_DIR}/share/metainfo/"

# Install script
cat > "${DIST_DIR}/install.sh" << 'INSTALL'
#!/bin/bash
# Install SteamLibraryManager to ~/.local/
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${HOME}/.local"

echo "Installing SteamLibraryManager to ${PREFIX}..."

# Copy library files
mkdir -p "${PREFIX}/lib/steam-library-manager"
cp -r "${SCRIPT_DIR}/lib/"* "${PREFIX}/lib/steam-library-manager/"

# Create launcher
mkdir -p "${PREFIX}/bin"
cat > "${PREFIX}/bin/steam-library-manager" << EOF
#!/bin/bash
export PYTHONPATH="${PREFIX}/lib/steam-library-manager:\${PYTHONPATH:-}"
exec python3 -m steam_library_manager.main "\$@"
EOF
chmod +x "${PREFIX}/bin/steam-library-manager"

# Desktop integration
mkdir -p "${PREFIX}/share/applications"
mkdir -p "${PREFIX}/share/icons/hicolor/scalable/apps"
mkdir -p "${PREFIX}/share/metainfo"
cp "${SCRIPT_DIR}/share/applications/"*.desktop "${PREFIX}/share/applications/"
cp "${SCRIPT_DIR}/share/icons/hicolor/scalable/apps/"*.svg \
    "${PREFIX}/share/icons/hicolor/scalable/apps/"
cp "${SCRIPT_DIR}/share/metainfo/"*.xml "${PREFIX}/share/metainfo/"

# Update caches
gtk-update-icon-cache -f -t "${PREFIX}/share/icons/hicolor" 2>/dev/null || true
update-desktop-database "${PREFIX}/share/applications" 2>/dev/null || true

echo "Done! Run with: steam-library-manager"
echo "Uninstall with: rm -rf ${PREFIX}/lib/steam-library-manager ${PREFIX}/bin/steam-library-manager"
INSTALL
chmod +x "${DIST_DIR}/install.sh"

# README
cat > "${DIST_DIR}/README.txt" << 'README'
Steam Library Manager — Portable Linux Distribution

QUICK START:
  ./bin/steam-library-manager

INSTALL (to ~/.local/):
  ./install.sh

REQUIREMENTS:
  Python 3.10+ with system Qt6 libraries.
  All Python dependencies are bundled.

UNINSTALL:
  rm -rf ~/.local/lib/steam-library-manager
  rm ~/.local/bin/steam-library-manager
  rm ~/.local/share/applications/io.github.switch_bros.SteamLibraryManager.desktop
README

# License
cp LICENSE "${DIST_DIR}/"

# Create tar.gz
cd dist
tar czf "${DIST_NAME}.tar.gz" "${DIST_NAME}"
cd ..

echo ""
echo "Created: dist/${DIST_NAME}.tar.gz"
echo "Size: $(du -h "dist/${DIST_NAME}.tar.gz" | cut -f1)"
