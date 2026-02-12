"""
UI Widgets Package.

This package contains custom Qt widgets used throughout the application:
- UIHelper: Static utility methods for common UI operations
- GameTreeWidget: Custom tree widget for displaying game categories
- ClickableImage: Clickable image widget with hover effects
- GameDetailsWidget: Detail panel showing game metadata (import directly to avoid circular deps)
"""

from __future__ import annotations

from src.ui.widgets.ui_helper import UIHelper
from src.ui.widgets.category_tree import GameTreeWidget
from src.ui.widgets.clickable_image import ClickableImage

__all__ = [
    'UIHelper',
    'GameTreeWidget',
    'ClickableImage',
]