#
# steam_library_manager/ui/dialogs/image_selection_dialog.py
# Dialog for selecting custom game artwork from SteamGridDB
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging

from PyQt6.QtCore import QPoint, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from steam_library_manager.config import config
from steam_library_manager.integrations.steamgrid_api import SteamGridDB
from steam_library_manager.ui.utils.font_helper import FontHelper
from steam_library_manager.ui.widgets.clickable_image import ClickableImage
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.open_url import open_url

logger = logging.getLogger("steamlibmgr.image_dialog")

__all__ = ["ImageSelectionDialog", "PagedSearchThread"]


class PagedSearchThread(QThread):
    """Fetch one page from SteamGridDB."""

    page_loaded = pyqtSignal(list, bool)

    def __init__(self, aid, itype, page=0, psize=24, game_id_override=None):
        super().__init__()
        self.aid = aid
        self.itype = itype
        self.page = page
        self.psize = psize
        self.game_id_override = game_id_override
        self.api = SteamGridDB()

    def run(self):
        imgs = self.api.get_images_by_type_paged(
            self.aid,
            self.itype,
            page=self.page,
            limit=self.psize,
            game_id_override=self.game_id_override,
        )
        more = len(imgs) >= self.psize
        self.page_loaded.emit(imgs, more)


class NameLookupThread(QThread):
    """Free-text search for a SteamGridDB game id by name."""

    finished_lookup = pyqtSignal(list)

    def __init__(self, term):
        super().__init__()
        self.term = term

    def run(self):
        results = SteamGridDB().search_games_by_name(self.term)
        self.finished_lookup.emit(results)


class ImageSelectionDialog(QDialog):
    """Browse and select game images."""

    def __init__(self, parent, name, aid, itype):
        super().__init__(parent)
        self.setWindowTitle(t("ui.dialogs.image_picker_title", type=t("ui.game_details.gallery.%s" % itype), game=name))
        self.resize(1100, 800)

        self.aid = aid
        self.game_name = name or ""
        self.itype = itype
        self.sel_url = None
        self.srch = None
        self.name_lookup = None
        # SteamGridDB game id chosen via manual search; None means auto-resolve from aid
        self.manual_game_id = None

        # pagination
        self._p = 0
        self._ps = 24
        self._done = False
        self._busy = False
        self._r = 0
        self._c = 0
        self._cnt = 0

        # throttling
        self._aq = []
        self._aa = 0
        self._MAXA = 3
        self._DA = 150

        self._sq = []
        self._sa = 0
        self._MAXS = 8

        # lazy loading
        self._lazy = []
        self._st = QTimer()
        self._st.setSingleShot(True)
        self._st.setInterval(50)
        self._st.timeout.connect(self._load_vis)

        self._mk_ui()
        self._check()

    def _mk_ui(self):
        self.ml = QVBoxLayout(self)

        # manual search row: lets the user override the auto-detected game
        # (essential for non-Steam shortcuts whose hash appids are unknown to SteamGridDB)
        srow = QHBoxLayout()
        srow.addWidget(QLabel(t("ui.image_browser.search_label")))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("ui.image_browser.search_placeholder"))
        self.search_input.setText(self.game_name)
        # noinspection PyUnresolvedReferences
        self.search_input.returnPressed.connect(self._do_name_lookup)
        srow.addWidget(self.search_input, 1)

        self.search_btn = QPushButton(t("ui.image_browser.search_button"))
        # noinspection PyUnresolvedReferences
        self.search_btn.clicked.connect(self._do_name_lookup)
        srow.addWidget(self.search_btn)

        self.search_results = QComboBox()
        self.search_results.hide()
        # noinspection PyUnresolvedReferences
        self.search_results.activated.connect(self._on_search_result_picked)
        srow.addWidget(self.search_results, 1)

        self.ml.addLayout(srow)

        self.sl = QLabel(t("ui.dialogs.image_picker_loading"))
        self.sl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ml.addWidget(self.sl)

        self.sc = QScrollArea()
        self.sc.setWidgetResizable(True)
        self.sc.hide()

        self.gw = QWidget()
        self.gl = QGridLayout(self.gw)
        self.gl.setSpacing(15)
        self.gl.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sc.setWidget(self.gw)
        self.sc.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.ml.addWidget(self.sc)

        # setup widget
        self.sw = QWidget()
        self.sw.hide()
        sl = QVBoxLayout(self.sw)
        sl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.setSpacing(20)

        tl = QLabel(t("settings.grid_setup.title"))
        tl.setFont(FontHelper.get_font(16, FontHelper.BOLD))
        tl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(tl)

        il = QLabel(
            t("settings.grid_setup.info")
            + "\n\n"
            + t("settings.grid_setup.step_1")
            + "\n"
            + t("settings.grid_setup.step_2")
            + "\n"
            + t("settings.grid_setup.step_3")
        )
        il.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(il)

        gb = QPushButton(t("settings.grid_setup.get_key_btn"))
        gb.setMinimumHeight(40)
        gb.clicked.connect(lambda: open_url("https://www.steamgriddb.com/profile/preferences/api"))
        sl.addWidget(gb)

        hl = QHBoxLayout()
        self.ki = QLineEdit()
        self.ki.setPlaceholderText(t("settings.api.placeholder"))
        self.ki.setMinimumHeight(35)
        hl.addWidget(self.ki)

        sb = QPushButton(t("common.save"))
        sb.setMinimumHeight(35)
        sb.clicked.connect(self._save)
        hl.addWidget(sb)

        sl.addLayout(hl)
        self.sw.setStyleSheet("background-color: #222; border-radius: 8px; padding: 20px;")

        self.ml.addWidget(self.sw)

        # cancel btn
        bl = QHBoxLayout()
        bl.addStretch()
        cb = QPushButton(t("common.cancel"))
        cb.clicked.connect(self.reject)
        bl.addWidget(cb)
        self.ml.addLayout(bl)

    def _check(self):
        api = SteamGridDB()
        if not api.api_key:
            self.sl.hide()
            self.sc.hide()
            self.sw.show()
            return
        self.sw.hide()
        # Non-Steam shortcuts have negative hash appids that SteamGridDB doesn't know.
        # Skip the doomed appid lookup and trigger a name search right away.
        if self._is_shortcut_appid(self.aid):
            self._do_name_lookup()
            return
        self._start()

    @staticmethod
    def _is_shortcut_appid(aid) -> bool:
        try:
            v = int(aid)
        except (TypeError, ValueError):
            return False
        return v <= 0 or v > 2_147_483_647

    def _do_name_lookup(self):
        term = self.search_input.text().strip()
        if not term:
            return
        # cancel any in-flight lookup
        if self.name_lookup is not None and self.name_lookup.isRunning():
            self.name_lookup.quit()
            self.name_lookup.wait(500)
        self.search_btn.setEnabled(False)
        self.search_results.hide()
        self.sl.setText(t("ui.image_browser.searching", term=term))
        self.sl.show()
        self.sc.hide()
        self.name_lookup = NameLookupThread(term)
        self.name_lookup.finished_lookup.connect(self._on_name_results)
        self.name_lookup.start()

    def _on_name_results(self, results: list):
        self.search_btn.setEnabled(True)
        if not results:
            self.sl.setText(t("ui.image_browser.no_matches"))
            self.search_results.hide()
            return

        self.search_results.blockSignals(True)
        self.search_results.clear()
        for r in results:
            label = r["name"]
            if r.get("release_date"):
                # only show year part (release_date is unix timestamp)
                try:
                    from datetime import datetime

                    yr = datetime.fromtimestamp(int(r["release_date"])).year
                    label = "%s (%d)" % (r["name"], yr)
                except (ValueError, TypeError, OSError):
                    pass
            self.search_results.addItem(label, r["id"])
        self.search_results.blockSignals(False)
        self.search_results.show()

        # auto-select the first hit and start loading covers
        self._on_search_result_picked(0)

    def _on_search_result_picked(self, idx: int):
        if idx < 0 or idx >= self.search_results.count():
            return
        gid = self.search_results.itemData(idx)
        if not isinstance(gid, int):
            return
        self.manual_game_id = gid
        self._start()

    def _save(self):
        k = self.ki.text().strip()
        if k:
            config.STEAMGRIDDB_API_KEY = k
            config.save()
            self._check()

    def _start(self):
        self._p = 0
        self._done = False
        self._busy = False
        self._r = 0
        self._c = 0
        self._cnt = 0

        self._aq.clear()
        self._aa = 0
        self._sq.clear()
        self._sa = 0
        self._lazy.clear()

        while self.gl.count():
            ch = self.gl.takeAt(0)
            if ch and ch.widget():
                ch.widget().deleteLater()

        self.sl.setText(t("ui.image_browser.loading_page", page=1))
        self.sl.show()
        self._load_p()

    def _load_p(self):
        if self._done or self._busy:
            return

        self._busy = True
        self.srch = PagedSearchThread(
            self.aid,
            self.itype,
            page=self._p,
            psize=self._ps,
            game_id_override=self.manual_game_id,
        )
        self.srch.page_loaded.connect(self._on_load)
        self.srch.start()

    def _on_load(self, items, more):
        self._busy = False

        if self._p == 0:
            self.sl.hide()
            self.sc.show()

        if not items and self._cnt == 0:
            self.sl.setText(t("ui.status.no_results"))
            self.sl.show()
            return

        self._add(items)
        self._cnt += len(items)

        QTimer.singleShot(50, self._load_vis)

        if more:
            self._p += 1
            QTimer.singleShot(100, self._load_p)
        else:
            self._done = True
            if self._cnt > 0:
                self.sl.setText(t("ui.image_browser.all_loaded", count=self._cnt))
                self.sl.show()

    def _add(self, items):
        sizes = {"grids": (4, 220, 330), "heroes": (2, 460, 215), "logos": (3, 300, 150), "icons": (6, 162, 162)}
        cols, w, h = sizes.get(self.itype, (3, 250, 250))

        r, c = self._r, self._c
        for it in items:
            box = QWidget()
            box.setFixedSize(w, h + 45)

            tags = [tg.lower() for tg in it.get("tags", [])]
            mime = it.get("mime", "").lower()

            url_l = it["url"].lower()
            th_l = it.get("thumb", "").lower()
            anim = (
                "webp" in mime
                or "gif" in mime
                or ("png" in mime and "animated" in tags)
                or "animated" in tags
                or url_l.endswith(".webm")
                or th_l.endswith(".webm")
            )

            bdgs = []
            if it.get("nsfw") or "nsfw" in tags:
                bdgs.append(("nsfw", "#d9534f"))
            if it.get("humor") or "humor" in tags:
                bdgs.append(("humor", "#f0ad4e"))
            if it.get("epilepsy") or "epilepsy" in tags:
                bdgs.append(("epilepsy", "#0275d8"))
            if anim:
                bdgs.append(("animated", "#5cb85c"))

            img = ClickableImage(box, w, h, metadata=it, external_badges=True)
            img.move(0, 5)

            if bdgs:
                ba = QWidget(box)
                ba.setGeometry(0, 0, w, 35)

                bl = QVBoxLayout(ba)
                bl.setContentsMargins(5, 0, 0, 0)
                bl.setSpacing(2)
                bl.setAlignment(Qt.AlignmentFlag.AlignTop)

                st = QWidget()
                sl = QHBoxLayout(st)
                sl.setContentsMargins(0, 0, 0, 0)
                sl.setSpacing(2)
                sl.setAlignment(Qt.AlignmentFlag.AlignLeft)

                for bt, col in bdgs:
                    s = QWidget()
                    s.setFixedSize(28, 5)
                    s.setStyleSheet("background-color: %s;" % col)
                    sl.addWidget(s)

                st.setFixedHeight(5)
                bl.addWidget(st)

                ic = QWidget()
                il = QHBoxLayout(ic)
                il.setContentsMargins(0, 0, 0, 0)
                il.setSpacing(2)
                il.setAlignment(Qt.AlignmentFlag.AlignLeft)

                for bt, col in bdgs:
                    ip = config.ICONS_DIR / ("flag_%s.webp" % bt)
                    lbl = QLabel()

                    if ip.exists():
                        px = QPixmap(str(ip)).scaledToHeight(24, Qt.TransformationMode.SmoothTransformation)
                        lbl.setPixmap(px)
                        lbl.setFixedSize(28, 28)
                        lbl.setStyleSheet(
                            "QLabel { background: %s; " "border-radius: 0 0 3px 3px; padding: 2px; }" % col
                        )
                    else:
                        tx = {
                            "nsfw": "%s %s" % (t("emoji.nsfw"), t("ui.badges.nsfw")),
                            "humor": "%s %s" % (t("emoji.humor"), t("ui.badges.humor")),
                            "epilepsy": "%s %s" % (t("emoji.blitz"), t("ui.badges.epilepsy")),
                            "animated": "%s %s" % (t("emoji.animated"), t("ui.badges.animated")),
                        }
                        lbl.setText(tx.get(bt, ""))
                        lbl.setFixedSize(28, 28)
                        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        lbl.setStyleSheet(
                            "background: %s; color: white; "
                            "border-radius: 0 0 4px 4px; font-weight: bold; "
                            "font-size: 9px; border: 1px solid rgba(255,255,255,0.3);" % col
                        )

                    il.addWidget(lbl)

                bl.addWidget(ic)
                ic.hide()
                ba.raise_()

                def eh(_, iw=ic):
                    iw.show()

                def lh(_, iw=ic):
                    iw.hide()

                box.enterEvent = eh
                box.leaveEvent = lh

            lurl = it["url"] if anim else it["thumb"]
            self._lazy.append([box, img, lurl, anim, False])

            def mk_clk(url, mt, tl):
                return lambda e: self._sel(url, mt, tl)

            img.mousePressEvent = mk_clk(it["url"], mime, tags)

            auth = it.get("author", {}).get("name") or t("common.unknown")
            al = QLabel(box)
            al.setText("👤 %s" % auth)
            al.setGeometry(0, h + 7, w, 30)
            al.setStyleSheet("color: #888; font-size: 10px;")
            al.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.gl.addWidget(box, r, c)
            c += 1
            if c >= cols:
                c = 0
                r += 1

        self._r = r
        self._c = c

    def _sel(self, url, mime="", tags=None):
        if tags is None:
            tags = []

        if url.endswith(".webm"):
            tl = [tg.lower() for tg in tags]
            if "png" in mime.lower() or "animated" in tl:
                url = url.replace(".webm", ".png")

        self.sel_url = url
        self.accept()

    def get_selected_url(self):
        return self.sel_url

    def _q_anim(self, w, url):
        self._aq.append((w, url))
        self._d_anim()

    def _d_anim(self):
        while self._aq and self._aa < self._MAXA:
            w, url = self._aq.pop(0)
            self._aa += 1
            w.load_finished.connect(self._on_a_done)
            w.load_image(url)

    def _on_a_done(self):
        self._aa = max(0, self._aa - 1)
        QTimer.singleShot(self._DA, self._d_anim)

    def _q_st(self, w, url):
        self._sq.append((w, url))
        self._d_st()

    def _d_st(self):
        while self._sq and self._sa < self._MAXS:
            w, url = self._sq.pop(0)
            self._sa += 1
            w.load_finished.connect(self._on_s_done)
            w.load_image(url)

    def _on_s_done(self):
        self._sa = max(0, self._sa - 1)
        self._d_st()

    def _on_scroll(self):
        self._st.start()

    def _load_vis(self):
        vp = self.sc.viewport()
        if vp is None:
            return

        vph = vp.height()
        m = 200

        for e in self._lazy:
            box, img, url, anim, ld = e
            if ld:
                continue

            pos = box.mapTo(vp, QPoint(0, 0))
            top = pos.y()
            bot = top + box.height()

            if bot < -m or top > vph + m:
                continue

            e[4] = True

            if anim:
                self._q_anim(img, url)
            else:
                self._q_st(img, url)
