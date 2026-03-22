#
# steam_library_manager/ui/widgets/autocat_method_selector.py
# Widget for selecting the auto-categorization method and options
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from steam_library_manager.config import config
from steam_library_manager.utils.i18n import t

__all__ = ["AutoCatMethodSelector"]

# Method key -> i18n checkbox label key
_METHOD_CHECKBOX_KEYS = (
    ("tags", "auto_categorize.option_tags"),
    ("publisher", "auto_categorize.by_publisher"),
    ("franchise", "auto_categorize.option_franchise"),
    ("genre", "auto_categorize.by_genre"),
    ("developer", "auto_categorize.by_developer"),
    ("platform", "auto_categorize.by_platform"),
    ("user_score", "auto_categorize.by_user_score"),
    ("hours_played", "auto_categorize.by_hours_played"),
    ("flags", "auto_categorize.by_flags"),
    ("vr", "auto_categorize.by_vr"),
    ("year", "auto_categorize.by_year"),
    ("hltb", "auto_categorize.by_hltb"),
    ("language", "auto_categorize.by_language"),
    ("deck_status", "auto_categorize.by_deck_status"),
    ("achievements", "auto_categorize.by_achievements"),
    ("pegi", "auto_categorize.by_pegi"),
    ("curator", "auto_categorize.by_curator"),
)


class AutoCatMethodSelector(QWidget):
    """Lets the user pick auto-categorization methods, tag settings,
    and scope (selected games vs. full library)."""

    methods_changed = pyqtSignal()

    def __init__(self, parent, games_count, all_games_count, category_name=None):
        super().__init__(parent)
        self._n_games = games_count
        self._n_all = all_games_count
        self._cat_name = category_name
        self._checkboxes = {}

        self._build()

    def _build(self):
        # create all UI components
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self._add_methods(lay)
        self._add_tags(lay)
        self._add_scope(lay)

        self.estimate_label = QLabel()
        self.estimate_label.setWordWrap(True)
        self.estimate_label.setStyleSheet("color: gray; font-style: italic;")
        lay.addWidget(self.estimate_label)

        self._wire()
        self._refresh_est()

    def _add_methods(self, parent_lay):
        # create method checkboxes grid with select/deselect buttons
        grp = QGroupBox(t("auto_categorize.method_group"))
        grid = QGridLayout()
        grid.setSpacing(4)

        cols = 3
        for i, (key, i18n_key) in enumerate(_METHOD_CHECKBOX_KEYS):
            cb = QCheckBox(t(i18n_key))
            self._checkboxes[key] = cb
            grid.addWidget(cb, i // cols, i % cols)

        # default: tags checked
        self._checkboxes["tags"].setChecked(True)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_all = QPushButton(t("auto_categorize.select_all"))
        btn_all.clicked.connect(self._sel_all)
        btn_row.addWidget(btn_all)

        btn_none = QPushButton(t("auto_categorize.deselect_all"))
        btn_none.clicked.connect(self._sel_none)
        btn_row.addWidget(btn_none)

        outer = QVBoxLayout()
        outer.addLayout(grid)
        outer.addLayout(btn_row)

        grp.setLayout(outer)
        parent_lay.addWidget(grp)

    def _add_tags(self, parent_lay):
        # create tags-specific settings group
        self.tags_group = QGroupBox(t("auto_categorize.settings"))
        tlay = QVBoxLayout()

        row = QHBoxLayout()
        row.addWidget(QLabel(t("auto_categorize.tags_per_game") + ":"))
        self.tags_count_spin = QSpinBox()
        self.tags_count_spin.setMinimum(1)
        self.tags_count_spin.setMaximum(50)
        self.tags_count_spin.setValue(config.TAGS_PER_GAME)
        row.addWidget(self.tags_count_spin)
        row.addStretch()
        tlay.addLayout(row)

        self.cb_ignore_common = QCheckBox(t("settings.tags.ignore_common"))
        self.cb_ignore_common.setChecked(config.IGNORE_COMMON_TAGS)
        tlay.addWidget(self.cb_ignore_common)

        self.tags_group.setLayout(tlay)
        parent_lay.addWidget(self.tags_group)

    def _add_scope(self, parent_lay):
        # create apply-to scope radio buttons
        grp = QGroupBox(t("auto_categorize.apply_group"))
        alay = QVBoxLayout()

        self.scope_group = QButtonGroup(self)

        if self._cat_name:
            txt = t(
                "auto_categorize.scope_category",
                name=self._cat_name,
                count=self._n_games,
            )
        else:
            txt = t("auto_categorize.scope_selected", count=self._n_games)

        self.rb_selected = QRadioButton(txt)
        self.rb_selected.setChecked(True)
        self.scope_group.addButton(self.rb_selected)
        alay.addWidget(self.rb_selected)

        self.rb_all = QRadioButton(t("auto_categorize.scope_all", count=self._n_all))
        self.scope_group.addButton(self.rb_all)
        alay.addWidget(self.rb_all)

        if self._n_games == self._n_all:
            self.rb_all.setChecked(True)

        grp.setLayout(alay)
        parent_lay.addWidget(grp)

    def _wire(self):
        # connect all internal signals to the change handler
        for cb in self._checkboxes.values():
            cb.toggled.connect(self._changed)

        self.tags_count_spin.valueChanged.connect(self._changed)
        self.rb_selected.toggled.connect(self._changed)
        self.rb_all.toggled.connect(self._changed)

    def _changed(self):
        # handle any setting change
        self._refresh_est()
        self.methods_changed.emit()

    def _refresh_est(self):
        # update the time estimate label based on current selections
        if not hasattr(self, "estimate_label") or not hasattr(self, "tags_group"):
            return

        self.tags_group.setVisible(self._checkboxes["tags"].isChecked())

        n = self._n_all if self.rb_all.isChecked() else self._n_games
        methods = self.get_selected_methods()

        if "tags" in methods:
            secs = int(n * 1.5)
            mins = secs // 60
            if mins > 0:
                time_str = t("auto_categorize.estimate_minutes", count=mins)
            else:
                time_str = t("auto_categorize.estimate_seconds", count=secs)
        else:
            time_str = t("auto_categorize.estimate_instant")

        self.estimate_label.setText(t("auto_categorize.estimate_label", time=time_str, games=n, methods=len(methods)))

    def _sel_all(self):
        for cb in self._checkboxes.values():
            cb.setChecked(True)

    def _sel_none(self):
        for cb in self._checkboxes.values():
            cb.setChecked(False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_selected_methods(self):
        # returns list of selected categorization method keys
        return [key for key, cb in self._checkboxes.items() if cb.isChecked()]

    def get_settings(self):
        # returns current selector settings as dict
        return {
            "scope": "all" if self.rb_all.isChecked() else "selected",
            "methods": self.get_selected_methods(),
            "tags_count": self.tags_count_spin.value(),
            "ignore_common": self.cb_ignore_common.isChecked(),
        }

    def apply_preset(self, methods, tags_count, ignore_common):
        # apply preset settings to the selector
        for key, cb in self._checkboxes.items():
            cb.setChecked(key in methods)
        self.tags_count_spin.setValue(tags_count)
        self.cb_ignore_common.setChecked(ignore_common)

    def is_curator_selected(self):
        # check if the curator method is currently selected
        cb = self._checkboxes.get("curator")
        return cb.isChecked() if cb else False
