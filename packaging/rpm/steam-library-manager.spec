%global app_id io.github.switch_bros.SteamLibraryManager

Name:           steam-library-manager
Version:        1.2.4
Release:        1%{?dist}
Summary:        A powerful Steam library organizer for Linux

License:        MIT
URL:            https://github.com/Switch-Bros/SteamLibraryManager
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-build
BuildRequires:  python3-installer
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel

Requires:       python3 >= 3.10
Requires:       python3-qt6
Requires:       python3-psutil
Requires:       python3-pillow
Requires:       python3-pyyaml
Requires:       python3-beautifulsoup4
Requires:       python3-lxml
Requires:       python3-requests
Requires:       python3-requests-oauthlib
Requires:       python3-qrcode
Requires:       python3-protobuf
Requires:       python3-packaging

Recommends:     python3-keyring

%description
The modern Depressurizer alternative. Organize your Steam library with
Smart Collections, AutoCat, Steam Deck optimization, achievement tracking,
HLTB integration, and more. Supports 17 auto-categorization types,
external game platforms, and full i18n (English/German).

%prep
%autosetup -n SteamLibraryManager-%{version}

%build
python3 -m build --wheel --no-isolation

%install
python3 -m installer --destdir=%{buildroot} dist/*.whl

# Desktop entry
install -Dm644 flatpak/%{app_id}.desktop \
    %{buildroot}%{_datadir}/applications/%{app_id}.desktop

# Icons
install -Dm644 steam_library_manager/resources/icon.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/%{app_id}.svg
install -Dm644 steam_library_manager/resources/icon.png \
    %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/%{app_id}.png

# Metainfo
install -Dm644 steam_library_manager/resources/%{app_id}.metainfo.xml \
    %{buildroot}%{_datadir}/metainfo/%{app_id}.metainfo.xml

# License
install -Dm644 LICENSE %{buildroot}%{_datadir}/licenses/%{name}/LICENSE

%files
%license LICENSE
%{_bindir}/steam-library-manager
%{python3_sitelib}/steam_library_manager/
%{python3_sitelib}/steam_library_manager-*.dist-info/
%{_datadir}/applications/%{app_id}.desktop
%{_datadir}/icons/hicolor/scalable/apps/%{app_id}.svg
%{_datadir}/icons/hicolor/512x512/apps/%{app_id}.png
%{_datadir}/metainfo/%{app_id}.metainfo.xml

%changelog
* Tue Mar 11 2026 SwitchBros <switchbros@proton.me> - 1.2.4-1
- Steam Deck responsive UI scaling
- Auto-sync library folders on startup
- Multi-format packaging (tar.gz, .deb, .rpm)
