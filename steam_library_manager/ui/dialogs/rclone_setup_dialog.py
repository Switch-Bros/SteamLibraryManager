#
# steam_library_manager/ui/dialogs/rclone_setup_dialog.py
# Built-in rclone setup wizard - no terminal needed
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# TODO: add more providers (Proton Drive, OneDrive)?

from __future__ import annotations

import platform
import subprocess
import zipfile
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
)

from steam_library_manager.core.logging import logger
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.utils.i18n import t

__all__ = ["RcloneSetupDialog"]

# supported providers with their rclone type and required fields
_PROVIDERS = {
    "MEGA": {
        "type": "mega",
        "fields": [
            ("user", "E-Mail", ""),
            ("pass", "Passwort", "password"),
        ],
    },
    "Google Drive": {
        "type": "drive",
        "fields": [],  # OAuth - handled differently
    },
    "Dropbox": {
        "type": "dropbox",
        "fields": [],  # OAuth
    },
    "Nextcloud (WebDAV)": {
        "type": "webdav",
        "fields": [
            ("url", "Server URL", ""),
            ("user", "Benutzername", ""),
            ("pass", "Passwort", "password"),
        ],
        "extra": {"vendor": "nextcloud"},
    },
    "WebDAV (andere)": {
        "type": "webdav",
        "fields": [
            ("url", "Server URL", ""),
            ("user", "Benutzername", ""),
            ("pass", "Passwort", "password"),
        ],
    },
}

_RCLONE_DL_URL = "https://downloads.rclone.org/rclone-current-%s-%s.zip"


class RcloneInstallThread(QThread):
    """Downloads and installs rclone to ~/.local/bin."""

    progress = pyqtSignal(str)
    finished_install = pyqtSignal(bool, str)

    def run(self):
        try:
            dest = Path.home() / ".local/bin"
            dest.mkdir(parents=True, exist_ok=True)

            # detect architecture
            arch = platform.machine()
            arch_map = {"x86_64": "amd64", "aarch64": "arm64", "armv7l": "arm-v7"}
            dl_arch = arch_map.get(arch, "amd64")

            url = _RCLONE_DL_URL % ("linux", dl_arch)
            self.progress.emit("Downloading rclone...")
            logger.info("Downloading rclone from %s" % url)

            import urllib.request

            zip_path = dest / "rclone.zip"
            urllib.request.urlretrieve(url, str(zip_path))

            self.progress.emit("Extracting...")
            with zipfile.ZipFile(str(zip_path), "r") as zf:
                # find the rclone binary inside the zip
                for name in zf.namelist():
                    if name.endswith("/rclone") and not name.endswith(".1"):
                        with zf.open(name) as src:
                            bin_path = dest / "rclone"
                            bin_path.write_bytes(src.read())
                            bin_path.chmod(0o755)
                            break

            zip_path.unlink()

            # verify it works
            r = subprocess.run(
                [str(dest / "rclone"), "version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0:
                ver = r.stdout.splitlines()[0] if r.stdout else "unknown"
                self.finished_install.emit(True, ver)
            else:
                self.finished_install.emit(False, t("cloud_sync.rclone_not_executable"))

        except Exception as exc:
            logger.error("rclone install failed: %s" % exc)
            self.finished_install.emit(False, str(exc))


class RcloneSetupDialog(BaseDialog):
    """Built-in wizard to install rclone and configure a remote."""

    def __init__(self, parent=None):
        self._thread = None
        self._field_inputs = {}
        super().__init__(
            parent=parent,
            title_text=t("cloud_sync.rclone_setup_title"),
            min_width=450,
            show_title_label=True,
            buttons="none",
        )

    def _build_content(self, layout):
        # rclone status
        from steam_library_manager.services.cloud_sync.rclone import _find_rclone

        rbin = _find_rclone()

        self.status_label = QLabel()
        if rbin:
            self.status_label.setText(t("cloud_sync.rclone_installed", path=rbin))
        else:
            self.status_label.setText(t("cloud_sync.rclone_not_found"))
        layout.addWidget(self.status_label)

        # install button (only if not found)
        self.btn_install = QPushButton(t("cloud_sync.rclone_download_btn"))
        self.btn_install.setVisible(not bool(rbin))
        self.btn_install.clicked.connect(self._install_rclone)
        layout.addWidget(self.btn_install)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        # provider selection
        layout.addWidget(QLabel(""))  # spacer
        layout.addWidget(QLabel(t("cloud_sync.rclone_provider_label")))

        self.combo_provider = QComboBox()
        for name in _PROVIDERS:
            self.combo_provider.addItem(name)
        self.combo_provider.currentTextChanged.connect(self._on_provider_changed)
        layout.addWidget(self.combo_provider)

        # dynamic credential fields
        self.form_widget = QLabel("")
        self.form_layout = QFormLayout()
        layout.addLayout(self.form_layout)

        # remote name
        self.remote_name = QLineEdit()
        self.remote_name.setPlaceholderText(t("cloud_sync.rclone_remote_name_hint"))
        self.form_layout.addRow(t("cloud_sync.rclone_remote_name_label"), self.remote_name)

        # oauth hint (hidden by default)
        self.oauth_hint = QLabel(t("cloud_sync.rclone_oauth_hint"))
        self.oauth_hint.setWordWrap(True)
        self.oauth_hint.setVisible(False)
        layout.addWidget(self.oauth_hint)

        # credential fields container
        self._cred_fields_layout = QFormLayout()
        layout.addLayout(self._cred_fields_layout)

        # trigger initial provider display
        self._on_provider_changed(self.combo_provider.currentText())

        # setup button
        self.btn_setup = QPushButton(t("cloud_sync.rclone_setup_btn"))
        self.btn_setup.clicked.connect(self._create_remote)
        self.btn_setup.setEnabled(bool(rbin))
        layout.addWidget(self.btn_setup)

        # result label
        self.result_label = QLabel("")
        layout.addWidget(self.result_label)

    def _on_provider_changed(self, name):
        # clear old fields
        self._field_inputs.clear()
        while self._cred_fields_layout.count():
            item = self._cred_fields_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        prov = _PROVIDERS.get(name, {})
        fields = prov.get("fields", [])

        if not fields:
            # oauth provider
            self.oauth_hint.setVisible(True)
        else:
            self.oauth_hint.setVisible(False)
            for key, label, mode in fields:
                inp = QLineEdit()
                if mode == "password":
                    inp.setEchoMode(QLineEdit.EchoMode.Password)
                self._field_inputs[key] = inp
                self._cred_fields_layout.addRow(label + ":", inp)

    def _install_rclone(self):
        self.btn_install.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)

        self._thread = RcloneInstallThread()
        self._thread.progress.connect(self._on_install_progress)
        self._thread.finished_install.connect(self._on_install_done)
        self._thread.start()

    def _on_install_progress(self, msg):
        self.progress_label.setText(msg)

    def _on_install_done(self, ok, msg):
        self.progress_bar.setVisible(False)
        if ok:
            self.status_label.setText(t("cloud_sync.rclone_installed", path=msg))
            self.btn_install.setVisible(False)
            self.btn_setup.setEnabled(True)
            self.progress_label.setText(t("cloud_sync.rclone_install_ok"))
        else:
            self.progress_label.setText(t("cloud_sync.rclone_install_error", error=msg))
            self.btn_install.setEnabled(True)

    def _create_remote(self):
        name = self.remote_name.text().strip()
        if not name:
            self.result_label.setText(t("cloud_sync.rclone_setup_no_name"))
            return

        # sanitize name (no spaces, no special chars)
        name = name.replace(" ", "_").replace(":", "")

        prov_name = self.combo_provider.currentText()
        prov = _PROVIDERS.get(prov_name, {})
        rtype = prov.get("type", "")

        from steam_library_manager.services.cloud_sync.rclone import _find_rclone

        rbin = _find_rclone()
        if not rbin:
            self.result_label.setText(t("cloud_sync.rclone_not_found"))
            return

        # build rclone config create command
        cmd = [rbin, "config", "create", name, rtype]

        # add extra params (e.g. vendor=nextcloud)
        extra = prov.get("extra", {})
        for k, v in extra.items():
            cmd.append("%s=%s" % (k, v))

        # add credential fields
        # rclone config create obscures passwords automatically,
        # so pass them in cleartext (no manual obscure step)
        fields = prov.get("fields", [])
        if fields:
            for key, _label, _mode in fields:
                inp = self._field_inputs.get(key)
                if inp:
                    cmd.append("%s=%s" % (key, inp.text()))

        self.btn_setup.setEnabled(False)
        self.result_label.setText(t("cloud_sync.rclone_setup_progress"))

        try:
            # for OAuth providers, we need to allow browser interaction
            if not fields:
                # OAuth flow - run in terminal-like mode
                r = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            else:
                r = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

            if r.returncode == 0:
                remote_str = "%s:" % name
                self.result_label.setText(t("cloud_sync.rclone_setup_ok", remote=remote_str))
                logger.info("rclone remote created: %s (%s)" % (name, rtype))
                # store the remote name for the caller
                self._created_remote = remote_str
            else:
                err = r.stderr.strip() or r.stdout.strip() or "unknown error"
                self.result_label.setText(t("cloud_sync.rclone_setup_error", error=err[:200]))
                logger.error("rclone config create failed: %s" % err)
        except subprocess.TimeoutExpired:
            self.result_label.setText(t("cloud_sync.rclone_setup_timeout"))
        except Exception as exc:
            self.result_label.setText(t("cloud_sync.rclone_setup_error", error=str(exc)))
        finally:
            self.btn_setup.setEnabled(True)

    @property
    def created_remote(self) -> str:
        return getattr(self, "_created_remote", "")
