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
    "steam_library_manager.core.appinfo_manager",
    "steam_library_manager.core.backup_manager",
    "steam_library_manager.core.cloud_storage_parser",
    "steam_library_manager.core.database",
    "steam_library_manager.core.database_importer",
    "steam_library_manager.core.game",
    "steam_library_manager.core.game_manager",
    "steam_library_manager.core.local_games_loader",
    "steam_library_manager.core.localconfig_helper",
    "steam_library_manager.core.logging",
    "steam_library_manager.core.packageinfo_parser",
    "steam_library_manager.core.steam_account",
    "steam_library_manager.core.steam_account_scanner",
    "steam_library_manager.core.steam_assets",
    "steam_library_manager.core.steam_login_manager",
    "steam_library_manager.core.token_store",
    "steam_library_manager.core.profile_manager",
]

SERVICE_MODULES: list[str] = [
    "steam_library_manager.services.asset_service",
    "steam_library_manager.services.autocategorize_service",
    "steam_library_manager.services.bootstrap_service",
    "steam_library_manager.services.category_service",
    "steam_library_manager.services.filter_service",
    "steam_library_manager.services.game_detail_service",
    "steam_library_manager.services.game_query_service",
    "steam_library_manager.services.game_service",
    "steam_library_manager.services.enrichment",
    "steam_library_manager.services.enrichment.enrichment_service",
    "steam_library_manager.services.enrichment.metadata_enrichment_service",
    "steam_library_manager.services.metadata_service",
    "steam_library_manager.services.search_service",
]

UTILS_MODULES: list[str] = [
    "steam_library_manager.utils.acf",
    "steam_library_manager.utils.appinfo",
    "steam_library_manager.utils.date_utils",
    "steam_library_manager.utils.i18n",
    "steam_library_manager.utils.manifest",
]

INTEGRATION_MODULES: list[str] = [
    "steam_library_manager.integrations.steam_store",
    "steam_library_manager.integrations.steamgrid_api",
]

TOP_LEVEL_MODULES: list[str] = [
    "steam_library_manager.config",
    "steam_library_manager.version",
]

# UI modules require PyQt6 at import time
_HAS_QT = importlib.util.find_spec("PyQt6") is not None

UI_MODULES: list[str] = [
    "steam_library_manager.ui.main_window",
    "steam_library_manager.ui.actions.edit_actions",
    "steam_library_manager.ui.actions.file_actions",
    "steam_library_manager.ui.actions.game_actions",
    "steam_library_manager.ui.actions.settings_actions",
    "steam_library_manager.ui.actions.steam_actions",
    "steam_library_manager.ui.actions.tools_actions",
    "steam_library_manager.ui.actions.profile_actions",
    "steam_library_manager.ui.actions.view_actions",
    "steam_library_manager.ui.builders.central_widget_builder",
    "steam_library_manager.ui.builders.menu_builder",
    "steam_library_manager.ui.builders.statusbar_builder",
    "steam_library_manager.ui.builders.toolbar_builder",
    "steam_library_manager.ui.dialogs.auto_categorize_dialog",
    "steam_library_manager.ui.dialogs.image_selection_dialog",
    "steam_library_manager.ui.dialogs.merge_duplicates_dialog",
    "steam_library_manager.ui.dialogs.metadata_dialogs",
    "steam_library_manager.ui.dialogs.missing_metadata_dialog",
    "steam_library_manager.ui.dialogs.pegi_selector_dialog",
    "steam_library_manager.ui.dialogs.profile_dialog",
    "steam_library_manager.ui.dialogs.profile_setup_dialog",
    "steam_library_manager.ui.dialogs.settings_dialog",
    "steam_library_manager.ui.dialogs.steam_modern_login_dialog",
    "steam_library_manager.ui.dialogs.steam_running_dialog",
    "steam_library_manager.ui.handlers.category_action_handler",
    "steam_library_manager.ui.handlers.category_change_handler",
    "steam_library_manager.ui.handlers.category_populator",
    "steam_library_manager.ui.handlers.data_load_handler",
    "steam_library_manager.ui.handlers.empty_collection_handler",
    "steam_library_manager.ui.handlers.selection_handler",
    "steam_library_manager.ui.utils.font_helper",
    "steam_library_manager.ui.utils.qt_utils",
    "steam_library_manager.ui.widgets.category_tree",
    "steam_library_manager.ui.widgets.clickable_image",
    "steam_library_manager.ui.widgets.game_details_widget",
    "steam_library_manager.ui.widgets.ui_helper",
    "steam_library_manager.ui.workers.game_load_worker",
    "steam_library_manager.ui.workers.session_restore_worker",
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
    from steam_library_manager.utils.i18n import init_i18n, t

    init_i18n("en")
    result = t("common.ok")
    assert isinstance(result, str)
    assert result != ""
    assert result != "[common.ok]"


def test_i18n_fallback() -> None:
    """Unknown keys return the bracket-wrapped key as fallback."""
    from steam_library_manager.utils.i18n import init_i18n, t

    init_i18n("en")
    result = t("this.key.does.not.exist")
    assert result == "[this.key.does.not.exist]"
