"""
UI Utility Package.

This package provides reusable UI helper functions organized into three modules:
- ui_helpers: Generic widget creation and styling
- dialog_helpers: Common dialog patterns
- qt_utils: Low-level Qt utilities
"""

# UI Helpers - Widget creation and styling
from src.ui.utils.ui_helpers import (
    create_splitter,
    create_search_bar,
    create_progress_dialog,
    create_labeled_widget,
    set_widget_margins,
    apply_dark_theme_to_widget,
)

# Dialog Helpers - Common dialog patterns
from src.ui.utils.dialog_helpers import (
    ask_confirmation,
    ask_text_input,
    ask_choice,
    show_warning,
    show_info,
    show_error,
    ask_yes_no_cancel,
)

# Qt Utils - Low-level Qt utilities
from src.ui.utils.qt_utils import (
    clear_layout,
    find_child_by_name,
    find_children_by_type,
    remove_widget_from_layout,
    set_all_widgets_enabled,
    get_layout_widgets,
    hide_all_children,
    show_all_children,
    disconnect_all_signals,
    count_visible_widgets,
)

__all__ = [
    # UI Helpers
    'create_splitter',
    'create_search_bar',
    'create_progress_dialog',
    'create_labeled_widget',
    'set_widget_margins',
    'apply_dark_theme_to_widget',
    # Dialog Helpers
    'ask_confirmation',
    'ask_text_input',
    'ask_choice',
    'show_warning',
    'show_info',
    'show_error',
    'ask_yes_no_cancel',
    # Qt Utils
    'clear_layout',
    'find_child_by_name',
    'find_children_by_type',
    'remove_widget_from_layout',
    'set_all_widgets_enabled',
    'get_layout_widgets',
    'hide_all_children',
    'show_all_children',
    'disconnect_all_signals',
    'count_visible_widgets',
]