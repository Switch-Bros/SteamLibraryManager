# src/ui/dialogs/merge_duplicates_dialog.py

"""Dialog for merging duplicate Steam collections.

Displays duplicate collection groups with radio buttons so the user can
choose which collection to keep per group.  Games from non-selected
duplicates are merged into the chosen one.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QWidget,
)

from src.ui.widgets.base_dialog import BaseDialog
from src.utils.i18n import t

__all__ = ["MergeDuplicatesDialog"]


class MergeDuplicatesDialog(BaseDialog):
    """Dialog for selecting which duplicate collections to keep.

    For each group of duplicate collections (same name), the user picks
    exactly one to keep.  Games from all others are merged into it.

    Attributes:
        _groups: Duplicate groups as ``{name: [collection, ...]}``.
        _button_groups: Maps group name to its QButtonGroup.
    """

    def __init__(
        self,
        parent: QWidget | None,
        duplicate_groups: dict[str, list[dict]],
        filter_name: str | None = None,
    ) -> None:
        """Initializes the merge duplicates dialog.

        Args:
            parent: Parent widget.
            duplicate_groups: Dict mapping collection name to list of
                duplicate collection dicts (from CloudStorageParser).
            filter_name: If set, only show the group with this name.
        """
        if filter_name and filter_name in duplicate_groups:
            self._groups: dict[str, list[dict]] = {filter_name: duplicate_groups[filter_name]}
        else:
            self._groups = duplicate_groups

        self._button_groups: dict[str, QButtonGroup] = {}

        super().__init__(
            parent,
            title_key="categories.merge_duplicates_title",
            min_width=550,
            show_title_label=True,
            buttons="custom",
        )
        self.setMinimumHeight(300)

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Creates the dialog UI with scrollable group boxes."""
        # Info text
        info = QLabel(t("categories.merge_duplicates_info"))
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; margin-bottom: 8px;")
        layout.addWidget(info)

        # Scroll area for groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        for name, collections in sorted(self._groups.items()):
            group_box = QGroupBox(t("categories.merge_duplicates_group", name=name, count=len(collections)))
            group_layout = QVBoxLayout()

            button_group = QButtonGroup(self)
            self._button_groups[name] = button_group

            for idx, coll in enumerate(collections):
                apps = coll.get("added", coll.get("apps", []))
                if not isinstance(apps, list):
                    apps = []
                game_count = len(apps)

                radio = QRadioButton(t("categories.merge_duplicates_entry", index=idx + 1, game_count=game_count))
                if idx == 0:
                    radio.setChecked(True)

                button_group.addButton(radio, idx)
                group_layout.addWidget(radio)

            group_box.setLayout(group_layout)
            scroll_layout.addWidget(group_box)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        merge_btn = QPushButton(t("categories.merge_duplicates_title"))
        merge_btn.setDefault(True)
        merge_btn.clicked.connect(self.accept)
        btn_layout.addWidget(merge_btn)

        layout.addLayout(btn_layout)

    def get_merge_plan(self) -> list[tuple[str, int]]:
        """Returns the merge plan based on user selections.

        Returns:
            List of ``(collection_name, keep_index)`` tuples indicating
            which collection index (0-based) to keep for each group.
        """
        plan: list[tuple[str, int]] = []
        for name, button_group in self._button_groups.items():
            checked_id = button_group.checkedId()
            if checked_id >= 0:
                plan.append((name, checked_id))
        return plan
