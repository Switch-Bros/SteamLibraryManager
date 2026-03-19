#
# steam_library_manager/ui/widgets/category_tree.py
# QTreeWidget for the hierarchical category/game sidebar
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#


from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QAbstractItemView

from steam_library_manager.config import config
from steam_library_manager.core.game_manager import Game
from steam_library_manager.integrations.external_games.models import get_collection_emoji
from steam_library_manager.utils.i18n import t

__all__ = ["GameTreeWidget"]


class GameTreeWidget(QTreeWidget):
    """Sidebar tree with categories, drag-drop, multi-select.

    Persists expanded/collapsed state in config.
    Emits signals for game clicks, right-clicks, and drops.
    """

    game_clicked = pyqtSignal(Game)
    game_right_clicked = pyqtSignal(Game, QPoint)
    category_right_clicked = pyqtSignal(str, QPoint)
    selection_changed = pyqtSignal(list)
    games_dropped = pyqtSignal(list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setIndentation(20)
        self.setAlternatingRowColors(False)

        # drag & drop
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.itemClicked.connect(self._on_click)
        self.itemSelectionChanged.connect(self._on_sel)
        self.itemExpanded.connect(self._on_expand)
        self.itemCollapsed.connect(self._on_collapse)

        self.setStyleSheet(
            "QTreeWidget::item { padding: 4px; }" " QTreeWidget::item:selected { background-color: #2d5a88; }"
        )

    def set_loading_state(self, loading):
        self.clear()
        if loading:
            ph = QTreeWidgetItem(self)
            ph.setText(0, t("common.loading"))
            ph.setFlags(Qt.ItemFlag.NoItemFlags)

    def populate_categories(
        self,
        categories,
        dynamic_collections=None,
        duplicate_info=None,
        smart_collections=None,
        external_platform_collections=None,
    ):
        # rebuild entire tree
        self.clear()

        dyn = dynamic_collections or set()
        dups = duplicate_info or {}
        sc = smart_collections or set()
        ext = external_platform_collections or set()

        for cat_name, games in categories.items():
            ci = QTreeWidgetItem(self)

            real = cat_name
            is_dup = cat_name in dups

            if is_dup:
                real, idx, total = dups[cat_name]
                disp = t("categories.duplicate_indicator", name=real, index=idx, total=total)
            else:
                disp = cat_name
                if cat_name in sc:
                    disp = "%s %s" % (cat_name, t("emoji.brain"))
                elif cat_name in dyn:
                    disp = "%s %s" % (cat_name, t("emoji.blitz"))
                elif cat_name in ext:
                    em = get_collection_emoji(cat_name)
                    if em:
                        disp = "%s %s" % (cat_name, em)

            ci.setText(0, t("categories.category_count", name=disp, count=len(games)))
            ci.setData(0, Qt.ItemDataRole.UserRole, "category")
            ci.setData(0, Qt.ItemDataRole.UserRole + 1, real)
            if is_dup:
                ci.setData(0, Qt.ItemDataRole.UserRole + 2, cat_name)

            ci.setExpanded(real in config.EXPANDED_CATEGORIES)

            for game in games:
                gi = QTreeWidgetItem(ci)
                gi.setText(0, game.name)
                gi.setData(0, Qt.ItemDataRole.UserRole, "game")
                gi.setData(0, Qt.ItemDataRole.UserRole + 1, game)

                dev = game.developer if game.developer else t("common.unknown")
                gi.setToolTip(0, t("categories.game_tooltip", name=game.name, developer=dev))

    @staticmethod
    def _on_expand(item):
        if item.data(0, Qt.ItemDataRole.UserRole) == "category":
            nm = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if nm and nm not in config.EXPANDED_CATEGORIES:
                config.EXPANDED_CATEGORIES.append(nm)
                config.save()

    @staticmethod
    def _on_collapse(item):
        if item.data(0, Qt.ItemDataRole.UserRole) == "category":
            nm = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if nm and nm in config.EXPANDED_CATEGORIES:
                config.EXPANDED_CATEGORIES.remove(nm)
                config.save()

    def _on_click(self, item, _col):
        if item.data(0, Qt.ItemDataRole.UserRole) == "game":
            g = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if g:
                self.game_clicked.emit(g)

    def _on_sel(self):
        # emit all selected games
        sel = [
            item.data(0, Qt.ItemDataRole.UserRole + 1)
            for item in self.selectedItems()
            if item.data(0, Qt.ItemDataRole.UserRole) == "game"
        ]
        self.selection_changed.emit(sel)

    def get_selected_categories(self):
        out = []
        for item in self.selectedItems():
            if item.data(0, Qt.ItemDataRole.UserRole) == "category":
                cn = item.data(0, Qt.ItemDataRole.UserRole + 1)
                if cn:
                    out.append(cn)
        return out

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if not item:
            return

        tp = item.data(0, Qt.ItemDataRole.UserRole)
        data = item.data(0, Qt.ItemDataRole.UserRole + 1)

        if tp == "game" and data:
            self.game_right_clicked.emit(data, event.globalPos())
        elif tp == "category" and data:
            sel = self.get_selected_categories()
            if len(sel) > 1:
                self.category_right_clicked.emit("__MULTI__", event.globalPos())
            else:
                self.category_right_clicked.emit(data, event.globalPos())

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        if item and item.data(0, Qt.ItemDataRole.UserRole) == "category":
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        # handle game drag onto category
        tgt = self.itemAt(event.position().toPoint())

        if not tgt or tgt.data(0, Qt.ItemDataRole.UserRole) != "category":
            event.ignore()
            return

        cat = tgt.data(0, Qt.ItemDataRole.UserRole + 1)

        dropped = []
        for item in self.selectedItems():
            if item.data(0, Qt.ItemDataRole.UserRole) == "game":
                dropped.append(item.data(0, Qt.ItemDataRole.UserRole + 1))

        if dropped:
            self.games_dropped.emit(dropped, cat)

        super().dropEvent(event)
