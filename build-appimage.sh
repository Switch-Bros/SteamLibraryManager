#!/bin/bash
# build-appimage.sh
set -e

cd "$(dirname "$0")"
rm -rf AppDir dist SteamLibraryManager-*.AppImage

# 1. PyInstaller bündelt alles in ein Verzeichnis
pip install pyinstaller==6.10.0
pyinstaller --onefile --windowed --name SteamLibraryManager --add-data "src/locales:locales" --add-data "resources:resources" src/main.py

# 2. linuxdeploy + Qt plugin bauen AppImage
wget -c "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
chmod +x linuxdeploy-x86_64.AppImage

wget -c "https://github.com/linuxdeploy/linuxdeploy-plugin-qt/releases/download/continuous/linuxdeploy-plugin-qt-x86_64.AppImage"
chmod +x linuxdeploy-plugin-qt-x86_64.AppImage

./linuxdeploy-x86_64.AppImage --appdir AppDir \
  --executable dist/SteamLibraryManager \
  --desktop-file resources/steam-library-manager.desktop \
  --icon-file resources/icon.png \
  --output appimage \
  --plugin qt

echo "✅ AppImage erstellt: $(ls SteamLibraryManager-*.AppImage)"
