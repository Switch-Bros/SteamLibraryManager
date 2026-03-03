"""
UI Widgets Package.

This package contains custom Qt widgets used throughout the application:
- UIHelper: Static utility methods for common UI operations
- GameTreeWidget: Custom tree widget for displaying game categories
- ClickableImage: Clickable image widget with hover effects
- InfoLabel: Styled key-value label + grid builder helper
- HorizontalCategoryList: Category checkboxes with tri-state support
- GameDetailsWidget: Detail panel (import directly to avoid circular deps)
"""

from __future__ import annotations

from steam_library_manager.ui.widgets.category_list import HorizontalCategoryList
from steam_library_manager.ui.widgets.category_tree import GameTreeWidget
from steam_library_manager.ui.widgets.clickable_image import ClickableImage
from steam_library_manager.ui.widgets.info_label import InfoLabel
from steam_library_manager.ui.widgets.ui_helper import UIHelper

__all__ = [
    "UIHelper",
    "GameTreeWidget",
    "ClickableImage",
    "InfoLabel",
    "HorizontalCategoryList",
]
