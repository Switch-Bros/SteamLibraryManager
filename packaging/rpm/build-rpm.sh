#!/bin/bash
# build-rpm.sh — Build .rpm package for Fedora/openSUSE
set -euo pipefail

cd "$(dirname "$0")/../.."

VERSION=$(python3 -c "exec(open('steam_library_manager/version.py').read()); print(__version__)")

echo "Building .rpm for SteamLibraryManager v${VERSION}..."

# Create rpmbuild tree
mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Create source tarball (tar from working dir — git archive not available in containers)
tar czf ~/rpmbuild/SOURCES/steam-library-manager-${VERSION}.tar.gz \
    --transform "s,^\\.,SteamLibraryManager-${VERSION}," \
    --exclude='.git' --exclude='dist' --exclude='__pycache__' --exclude='*.egg-info' \
    .

# Copy spec (with version substitution)
sed "s/^Version:.*/Version:        ${VERSION}/" \
    packaging/rpm/steam-library-manager.spec > ~/rpmbuild/SPECS/steam-library-manager.spec

# Build
rpmbuild -ba ~/rpmbuild/SPECS/steam-library-manager.spec

echo ""
echo "RPMs created in ~/rpmbuild/RPMS/"
ls -lh ~/rpmbuild/RPMS/noarch/ 2>/dev/null || true
