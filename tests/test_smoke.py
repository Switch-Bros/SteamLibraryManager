"""Smoke tests – verify all modules are importable and free of syntax errors.

This is an infrastructure test (not a unit test), so it lives in the tests
root rather than under ``tests/unit/``.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys

import pytest

# ---------------------------------------------------------------------------
# Module lists
# ---------------------------------------------------------------------------

CORE_MODULES: list[str] = [
    "src.core.appinfo_manager",
    "src.core.backup_manager",
    "src.core.cloud_storage_parser",
    "src.core.database",
    "src.core.database_importer",
    "src.core.game",
    "src.core.game_manager",
    "src.core.local_games_loader",
    "src.core.localconfig_helper",
    "src.core.logging",
    "src.core.non_game_apps",
    "src.core.packageinfo_parser",
    "src.core.steam_account",
    "src.core.steam_account_scanner",
    "src.core.steam_assets",
    "src.core.steam_login_manager",
    "src.core.token_store",
]

SERVICE_MODULES: list[str] = [
    "src.services.asset_service",
    "src.services.autocategorize_service",
    "src.services.bootstrap_service",
    "src.services.category_service",
    "src.services.filter_service",
    "src.services.game_detail_service",
    "src.services.game_query_service",
    "src.services.game_service",
    "src.services.metadata_enrichment_service",
    "src.services.metadata_service",
    "src.services.search_service",
]

UTILS_MODULES: list[str] = [
    "src.utils.acf",
    "src.utils.appinfo",
    "src.utils.date_utils",
    "src.utils.i18n",
    "src.utils.manifest",
]

INTEGRATION_MODULES: list[str] = [
    "src.integrations.steam_store",
    "src.integrations.steamgrid_api",
]

TOP_LEVEL_MODULES: list[str] = [
    "src.config",
    "src.version",
]

# UI modules require PyQt6 at import time
_HAS_QT = importlib.util.find_spec("PyQt6") is not None

UI_MODULES: list[str] = [
    "src.ui.main_window",
    "src.ui.actions.edit_actions",
    "src.ui.actions.file_actions",
    "src.ui.actions.game_actions",
    "src.ui.actions.settings_actions",
    "src.ui.actions.steam_actions",
    "src.ui.actions.tools_actions",
    "src.ui.actions.view_actions",
    "src.ui.builders.central_widget_builder",
    "src.ui.builders.menu_builder",
    "src.ui.builders.statusbar_builder",
    "src.ui.builders.toolbar_builder",
    "src.ui.dialogs.auto_categorize_dialog",
    "src.ui.dialogs.image_selection_dialog",
    "src.ui.dialogs.merge_duplicates_dialog",
    "src.ui.dialogs.metadata_dialogs",
    "src.ui.dialogs.missing_metadata_dialog",
    "src.ui.dialogs.pegi_selector_dialog",
    "src.ui.dialogs.profile_setup_dialog",
    "src.ui.dialogs.settings_dialog",
    "src.ui.dialogs.steam_modern_login_dialog",
    "src.ui.dialogs.steam_running_dialog",
    "src.ui.handlers.category_action_handler",
    "src.ui.handlers.category_change_handler",
    "src.ui.handlers.category_populator",
    "src.ui.handlers.data_load_handler",
    "src.ui.handlers.empty_collection_handler",
    "src.ui.handlers.selection_handler",
    "src.ui.utils.dialog_helpers",
    "src.ui.utils.font_helper",
    "src.ui.utils.qt_utils",
    "src.ui.utils.ui_helpers",
    "src.ui.widgets.category_tree",
    "src.ui.widgets.clickable_image",
    "src.ui.widgets.game_details_widget",
    "src.ui.widgets.ui_helper",
    "src.ui.workers.game_load_worker",
    "src.ui.workers.session_restore_worker",
]


# ---------------------------------------------------------------------------
# Parametrized import tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_path", CORE_MODULES)
def test_import_core_modules(module_path: str) -> None:
    """Core module must be importable without errors."""
    importlib.import_module(module_path)


@pytest.mark.parametrize("module_path", SERVICE_MODULES)
def test_import_service_modules(module_path: str) -> None:
    """Service module must be importable without errors."""
    importlib.import_module(module_path)


@pytest.mark.parametrize("module_path", UTILS_MODULES)
def test_import_utils_modules(module_path: str) -> None:
    """Utils module must be importable without errors."""
    importlib.import_module(module_path)


@pytest.mark.parametrize("module_path", INTEGRATION_MODULES)
def test_import_integration_modules(module_path: str) -> None:
    """Integration module must be importable without errors."""
    importlib.import_module(module_path)


@pytest.mark.parametrize("module_path", TOP_LEVEL_MODULES)
def test_import_top_level_modules(module_path: str) -> None:
    """Top-level module must be importable without errors."""
    importlib.import_module(module_path)


@pytest.mark.skipif(not _HAS_QT, reason="PyQt6 not installed")
@pytest.mark.parametrize("module_path", UI_MODULES)
def test_import_ui_modules(module_path: str) -> None:
    """UI module must be importable when PyQt6 is available.

    No QApplication needed – importing modules only defines classes/functions
    without instantiating widgets.
    """
    importlib.import_module(module_path)


# ---------------------------------------------------------------------------
# Circular import check
# ---------------------------------------------------------------------------


def test_no_circular_imports() -> None:
    """All non-UI modules can be imported in a fresh subprocess without cycles.

    Uses subprocess isolation to avoid corrupting module references for
    other tests in the same session.
    """
    import subprocess

    all_modules = CORE_MODULES + SERVICE_MODULES + UTILS_MODULES + INTEGRATION_MODULES + TOP_LEVEL_MODULES
    import_lines = "; ".join(f"import {m}" for m in all_modules)
    result = subprocess.run(
        [sys.executable, "-c", import_lines],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Circular import detected:\nstderr: {result.stderr}"


# ---------------------------------------------------------------------------
# i18n smoke tests
# ---------------------------------------------------------------------------


def test_i18n_loads() -> None:
    """The t() function returns a real translation for a known key."""
    from src.utils.i18n import init_i18n, t

    init_i18n("en")
    result = t("common.ok")
    assert isinstance(result, str)
    assert result != ""
    assert result != "[common.ok]"


def test_i18n_fallback() -> None:
    """Unknown keys return the bracket-wrapped key as fallback."""
    from src.utils.i18n import init_i18n, t

    init_i18n("en")
    result = t("this.key.does.not.exist")
    assert result == "[this.key.does.not.exist]"
