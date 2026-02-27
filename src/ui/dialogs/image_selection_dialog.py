# src/ui/image_selection_dialog.py

"""
Dialog for selecting game images from SteamGridDB.

This module provides a dialog that allows users to browse and select images
(grids, heroes, logos, icons) from SteamGridDB for their games. It includes
API key setup functionality and threaded image loading.
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QScrollArea,
    QWidget,
    QGridLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QHBoxLayout,
)

from src.config import config
from src.integrations.steamgrid_api import SteamGridDB
from src.ui.utils.font_helper import FontHelper
from src.ui.widgets.clickable_image import ClickableImage
from src.utils.i18n import t
from src.utils.open_url import open_url

logger = logging.getLogger("steamlibmgr.image_dialog")

__all__ = ["ImageSelectionDialog", "PagedSearchThread"]


class PagedSearchThread(QThread):
    """Background thread for fetching one page of images from SteamGridDB.

    Fetches a single page and emits the results. The dialog requests
    the next page after the current one is displayed.

    Signals:
        page_loaded: Emitted with (images, has_more) per page.
    """

    page_loaded = pyqtSignal(list, bool)

    def __init__(self, app_id: int, img_type: str, page: int = 0, page_size: int = 24) -> None:
        """Initializes the paged search thread.

        Args:
            app_id: The Steam app ID to fetch images for.
            img_type: Image type ('grids', 'heroes', 'logos', 'icons').
            page: Page number (0-indexed).
            page_size: Results per page.
        """
        super().__init__()
        self.app_id = app_id
        self.img_type = img_type
        self.page = page
        self.page_size = page_size
        self.api = SteamGridDB()

    def run(self) -> None:
        """Fetches one page of images and emits the result."""
        images = self.api.get_images_by_type_paged(
            self.app_id,
            self.img_type,
            page=self.page,
            limit=self.page_size,
        )
        has_more = len(images) >= self.page_size
        self.page_loaded.emit(images, has_more)


class ImageSelectionDialog(QDialog):
    """
    Dialog for browsing and selecting game images from SteamGridDB.

    This dialog allows users to browse available images for a game and select
    one to use. It includes functionality for setting up the SteamGridDB API
    key if it's not configured.

    Attributes:
        app_id (int): The Steam app ID of the game.
        img_type (str): The type of images to display ('grids', 'heroes', 'logos', 'icons').
        selected_url (str): The URL of the selected image.
        searcher (SearchThread): The background thread for fetching images.
        main_layout (QVBoxLayout): The main layout of the dialog.
        status_label (QLabel): Label for displaying status messages.
        scroll (QScrollArea): Scroll area for the image grid.
        grid_widget (QWidget): Widget containing the image grid.
        grid_layout (QGridLayout): Layout for arranging images in a grid.
        setup_widget (QWidget): Widget for API key setup.
        key_input (QLineEdit): Input field for entering the API key.
    """

    def __init__(self, parent, game_name, app_id, img_type):
        """
        Initializes the image selection dialog.

        Args:
            parent: Parent widget.
            game_name (str): The name of the game.
            app_id (int): The Steam app ID of the game.
            img_type (str): The type of images to display ('grids', 'heroes', 'logos', 'icons').
        """
        super().__init__(parent)
        self.setWindowTitle(
            t("ui.dialogs.image_picker_title", type=t(f"ui.game_details.gallery.{img_type}"), game=game_name)
        )
        self.resize(1100, 800)

        self.app_id = app_id
        self.img_type = img_type
        self.selected_url = None
        self.searcher = None

        # Pagination state
        self._current_page: int = 0
        self._page_size: int = 24
        self._all_loaded: bool = False
        self._loading: bool = False
        self._grid_row: int = 0
        self._grid_col: int = 0
        self._total_images: int = 0

        # Throttling for animated image loading
        self._animated_load_queue: list[tuple] = []
        self._animated_loading_count: int = 0
        self._MAX_CONCURRENT_ANIMATED: int = 3
        self._ANIMATED_DELAY_MS: int = 150

        self._create_ui()
        self._check_api_and_start()

    def _create_ui(self):
        """Creates the user interface for the dialog."""
        self.main_layout = QVBoxLayout(self)

        # Status / Loading Label
        self.status_label = QLabel(t("ui.dialogs.image_picker_loading"))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.status_label)

        # Scroll Area for results
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.hide()

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.grid_widget)

        self.main_layout.addWidget(self.scroll)

        # --- SETUP WIDGET (If API Key is missing) ---
        self.setup_widget = QWidget()
        self.setup_widget.hide()
        setup_layout = QVBoxLayout(self.setup_widget)
        setup_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        setup_layout.setSpacing(20)

        title_lbl = QLabel(t("settings.grid_setup.title"))
        title_lbl.setFont(FontHelper.get_font(16, FontHelper.BOLD))
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        setup_layout.addWidget(title_lbl)

        info_lbl = QLabel(
            t("settings.grid_setup.info")
            + "\n\n"
            + t("settings.grid_setup.step_1")
            + "\n"
            + t("settings.grid_setup.step_2")
            + "\n"
            + t("settings.grid_setup.step_3")
        )
        info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        setup_layout.addWidget(info_lbl)

        get_key_btn = QPushButton(t("settings.grid_setup.get_key_btn"))
        get_key_btn.setMinimumHeight(40)
        get_key_btn.clicked.connect(lambda: open_url("https://www.steamgriddb.com/profile/preferences/api"))
        setup_layout.addWidget(get_key_btn)

        input_layout = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText(t("settings.grid_setup.key_placeholder"))
        self.key_input.setMinimumHeight(35)
        input_layout.addWidget(self.key_input)

        save_btn = QPushButton(t("common.save"))
        save_btn.setMinimumHeight(35)
        save_btn.clicked.connect(self._save_key_and_reload)
        input_layout.addWidget(save_btn)

        setup_layout.addLayout(input_layout)
        self.setup_widget.setStyleSheet("background-color: #222; border-radius: 8px; padding: 20px;")

        self.main_layout.addWidget(self.setup_widget)

        # Cancel Button at the bottom
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        self.main_layout.addLayout(btn_layout)

    def _check_api_and_start(self):
        """
        Checks if the SteamGridDB API key is configured and starts the search.

        If the API key is missing, displays the setup widget. Otherwise, starts
        the image search.
        """
        api = SteamGridDB()
        if not api.api_key:
            self.status_label.hide()
            self.scroll.hide()
            self.setup_widget.show()
        else:
            self.setup_widget.hide()
            self._start_search()

    def _save_key_and_reload(self):
        """Saves the entered API key to the config and restarts the search.

        Sets the key on the config singleton and persists via config.save().
        """
        key = self.key_input.text().strip()
        if key:
            config.STEAMGRIDDB_API_KEY = key
            config.save()
            self._check_api_and_start()

    def _start_search(self):
        """Starts paginated image loading from page 0.

        Resets pagination state, clears the grid, and loads the first page.
        """
        # Reset pagination state
        self._current_page = 0
        self._all_loaded = False
        self._loading = False
        self._grid_row = 0
        self._grid_col = 0
        self._total_images = 0

        # Reset animated loading queue
        self._animated_load_queue.clear()
        self._animated_loading_count = 0

        # Clear existing grid
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child and child.widget():
                child.widget().deleteLater()

        self.status_label.setText(t("ui.image_browser.loading_page", page=1))
        self.status_label.show()
        self._load_next_page()

    def _load_next_page(self) -> None:
        """Loads the next page of images in a background thread."""
        if self._all_loaded or self._loading:
            return

        self._loading = True
        self.searcher = PagedSearchThread(
            self.app_id,
            self.img_type,
            page=self._current_page,
            page_size=self._page_size,
        )
        self.searcher.page_loaded.connect(self._on_page_loaded)
        self.searcher.start()

    def _on_page_loaded(self, items: list, has_more: bool) -> None:
        """Handles a loaded page: appends images and optionally loads next.

        Args:
            items: List of image data dicts for this page.
            has_more: True if there are more pages to load.
        """
        self._loading = False

        # First page: hide status, show scroll area
        if self._current_page == 0:
            self.status_label.hide()
            self.scroll.show()

        if not items and self._total_images == 0:
            self.status_label.setText(t("ui.status.no_results"))
            self.status_label.show()
            return

        # Append images to grid
        self._append_images_to_grid(items)
        self._total_images += len(items)

        if has_more:
            self._current_page += 1
            # Small delay to let UI breathe, then load next page
            QTimer.singleShot(100, self._load_next_page)
        else:
            self._all_loaded = True
            if self._total_images > 0:
                self.status_label.setText(t("ui.image_browser.all_loaded", count=self._total_images))
                self.status_label.show()

    def _append_images_to_grid(self, items: list) -> None:
        """Appends image widgets to the grid from a page of results.

        Args:
            items: List of image data dicts to display.
        """
        config_map = {"grids": (4, 220, 330), "heroes": (2, 460, 215), "logos": (3, 300, 150), "icons": (6, 162, 162)}
        cols, w, h = config_map.get(self.img_type, (3, 250, 250))

        row, col = self._grid_row, self._grid_col
        for item in items:
            # Container fixed size
            container = QWidget()
            container.setFixedSize(w, h + 45)

            # FIX: Use 'tag' instead of 't' to avoid shadowing the global translation function
            tags = [tag.lower() for tag in item.get("tags", [])]
            mime = item.get("mime", "").lower()

            # Check for APNG: often labeled as 'image/png' but has 'animated' tag
            # We treat it as animated if it has the tag, so we load the FULL URL later.
            # Check if animated (including WEBM detection via URL)
            url_lower = item["url"].lower()
            thumb_lower = item.get("thumb", "").lower()
            is_animated = (
                "webp" in mime
                or "gif" in mime
                or ("png" in mime and "animated" in tags)
                or "animated" in tags
                or url_lower.endswith(".webm")  # WEBM is always animated!
                or thumb_lower.endswith(".webm")  # Thumbnail can also be WEBM!
            )

            badge_info = []
            if item.get("nsfw") or "nsfw" in tags:
                badge_info.append(("nsfw", "#d9534f"))
            if item.get("humor") or "humor" in tags:
                badge_info.append(("humor", "#f0ad4e"))
            if item.get("epilepsy") or "epilepsy" in tags:
                badge_info.append(("epilepsy", "#0275d8"))
            if is_animated:
                badge_info.append(("animated", "#5cb85c"))

            # IMAGE IMMER BEI y=5! (auch ohne Badges)
            img_widget = ClickableImage(container, w, h, metadata=item, external_badges=True)
            img_widget.move(0, 5)

            # BADGES NUR wenn vorhanden
            if badge_info:
                badge_area = QWidget(container)
                badge_area.setGeometry(0, 0, w, 35)

                area_layout = QVBoxLayout(badge_area)
                area_layout.setContentsMargins(5, 0, 0, 0)
                area_layout.setSpacing(2)
                area_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

                # Lippen
                stripes = QWidget()
                stripes_layout = QHBoxLayout(stripes)
                stripes_layout.setContentsMargins(0, 0, 0, 0)
                stripes_layout.setSpacing(2)
                stripes_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

                for badge_type, color in badge_info:
                    s = QWidget()
                    s.setFixedSize(28, 5)
                    s.setStyleSheet(f"background-color: {color};")
                    stripes_layout.addWidget(s)

                stripes.setFixedHeight(5)
                area_layout.addWidget(stripes)

                # Icons
                icons = QWidget()
                icons_layout = QHBoxLayout(icons)
                icons_layout.setContentsMargins(0, 0, 0, 0)
                icons_layout.setSpacing(2)
                icons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

                for badge_type, color in badge_info:
                    icon_path = config.ICONS_DIR / f"flag_{badge_type}.png"
                    lbl = QLabel()

                    if icon_path.exists():
                        pix = QPixmap(str(icon_path)).scaledToHeight(28, Qt.TransformationMode.SmoothTransformation)
                        lbl.setPixmap(pix)
                        lbl.setFixedSize(28, 28)
                        lbl.setStyleSheet(
                            "QLabel { border: 1px solid rgba(0,0,0,0.5); "
                            "border-radius: 0 0 3px 3px; "
                            "background: rgba(0,0,0,0.35); padding: 2px; }"
                        )
                    else:
                        texts = {
                            "nsfw": f"{t('emoji.nsfw')} {t('ui.badges.nsfw')}",
                            "humor": f"{t('emoji.humor')} {t('ui.badges.humor')}",
                            "epilepsy": f"{t('emoji.blitz')} {t('ui.badges.epilepsy')}",
                            "animated": f"{t('emoji.animated')} {t('ui.badges.animated')}",
                        }
                        lbl.setText(texts.get(badge_type, ""))
                        lbl.setFixedSize(28, 28)
                        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        lbl.setStyleSheet(
                            f"background: {color}; color: white; "
                            f"border-radius: 0 0 4px 4px; font-weight: bold; "
                            f"font-size: 9px; border: 1px solid rgba(255,255,255,0.3);"
                        )

                    icons_layout.addWidget(lbl)

                area_layout.addWidget(icons)
                icons.hide()
                badge_area.raise_()

                # HOVER - RICHTIG mit closure!
                def enter_handler(_, icon_widget=icons):
                    icon_widget.show()

                def leave_handler(_, icon_widget=icons):
                    icon_widget.hide()

                container.enterEvent = enter_handler
                container.leaveEvent = leave_handler

            # Smart loading: FULL for animated (WEBM, WEBP, GIF), thumbnail for static
            # Animated images use throttled loading to prevent UI freezes
            if is_animated:
                self._queue_animated_load(img_widget, item["url"])
            else:
                img_widget.load_image(item["thumb"])  # Thumbnail — instant, no throttle

            # When user clicks, select the full URL and convert WEBM to PNG if needed
            def make_click_handler(url, mime_type, tag_list):
                return lambda e: self._on_select(url, mime_type, tag_list)

            img_widget.mousePressEvent = make_click_handler(item["url"], mime, tags)

            # Author
            author_name = item.get("author", {}).get("name") or t("ui.game_details.value_unknown")
            lbl_author = QLabel(container)
            lbl_author.setText(f"👤 {author_name}")
            lbl_author.setGeometry(0, h + 7, w, 30)
            lbl_author.setStyleSheet("color: #888; font-size: 10px;")
            lbl_author.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.grid_layout.addWidget(container, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1

        # Save position for next page
        self._grid_row = row
        self._grid_col = col

    def _on_select(self, url, mime="", tags=None):
        """
        Handles image selection.

        This method is called when the user clicks on an image. It stores the
        selected URL and closes the dialog. For APNG images served as WEBM,
        it converts the URL to PNG format.

        Args:
            url (str): The URL of the selected image.
            mime (str): The MIME type of the image.
            tags (list): List of tags associated with the image.
        """
        if tags is None:
            tags = []

        # Convert WEBM to PNG for APNG downloads
        # SteamGridDB serves APNG as .webm preview but .png download
        if url.endswith(".webm"):
            # Check if this is an APNG (PNG + animated tag)
            tags_lower = [tag.lower() for tag in tags]
            if "png" in mime.lower() or "animated" in tags_lower:
                url = url.replace(".webm", ".png")

        self.selected_url = url
        self.accept()

    def get_selected_url(self):
        """
        Gets the URL of the selected image.

        Returns:
            str: The URL of the selected image, or None if no image was selected.
        """
        return self.selected_url

    # ── Animated image throttling ──────────────────────────────────

    def _queue_animated_load(self, widget: ClickableImage, url: str) -> None:
        """Queue an animated image for throttled loading.

        Args:
            widget: The ClickableImage widget to load the image into.
            url: The URL of the animated image to load.
        """
        self._animated_load_queue.append((widget, url))
        self._process_animated_queue()

    def _process_animated_queue(self) -> None:
        """Process the animated load queue up to the concurrency limit."""
        while self._animated_load_queue and self._animated_loading_count < self._MAX_CONCURRENT_ANIMATED:
            widget, url = self._animated_load_queue.pop(0)
            self._animated_loading_count += 1
            widget.load_finished.connect(self._on_animated_load_finished)
            widget.load_image(url)

    def _on_animated_load_finished(self) -> None:
        """Handle completion of an animated image load.

        Decrements the counter and schedules the next queue processing
        with a small delay to avoid overwhelming the UI.
        """
        self._animated_loading_count = max(0, self._animated_loading_count - 1)
        QTimer.singleShot(self._ANIMATED_DELAY_MS, self._process_animated_queue)
