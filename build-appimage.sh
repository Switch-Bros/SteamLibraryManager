#!/bin/bash
# build-appimage.sh — Build SLM AppImage
# Usage: ./build-appimage.sh
set -euo pipefail

cd "$(dirname "$0")"
echo "Building SteamLibraryManager AppImage..."

# Clean previous builds
rm -rf AppDir dist build SteamLibraryManager-*.AppImage

# 1. Bundle with PyInstaller (--windowed, NOT --onefile — linuxdeploy needs a directory)
pip install --break-system-packages pyinstaller 2>/dev/null || pip install pyinstaller
pyinstaller \
    --name SteamLibraryManager \
    --windowed \
    --noconfirm \
    --add-data "resources:resources" \
    --add-data "src:src" \
    src/main.py

# 2. Create AppDir structure
mkdir -p AppDir/usr/{bin,share/{applications,icons/hicolor/scalable/apps,metainfo}}

# Copy PyInstaller output
cp -r dist/SteamLibraryManager/* AppDir/usr/bin/

# Copy desktop integration files
cp flatpak/org.steamlibrarymanager.SteamLibraryManager.desktop \
    AppDir/usr/share/applications/
cp flatpak/org.steamlibrarymanager.svg \
    AppDir/usr/share/icons/hicolor/scalable/apps/
cp resources/org.steamlibrarymanager.metainfo.xml \
    AppDir/usr/share/metainfo/

# AppRun needs these at the top level too
cp flatpak/org.steamlibrarymanager.SteamLibraryManager.desktop AppDir/
cp flatpak/org.steamlibrarymanager.svg AppDir/

# 3. Download linuxdeploy (if not cached)
LINUXDEPLOY="linuxdeploy-x86_64.AppImage"
if [ ! -f "$LINUXDEPLOY" ]; then
    wget -q "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/${LINUXDEPLOY}"
    chmod +x "$LINUXDEPLOY"
fi

# 4. Build AppImage
ARCH=x86_64 ./"$LINUXDEPLOY" \
    --appdir AppDir \
    --desktop-file AppDir/org.steamlibrarymanager.SteamLibraryManager.desktop \
    --icon-file AppDir/org.steamlibrarymanager.svg \
    --output appimage

RESULT=$(ls SteamLibraryManager-*.AppImage 2>/dev/null)
echo ""
echo "AppImage created: ${RESULT}"
echo "Test with: ./${RESULT}"
