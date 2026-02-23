"""Centralized theme constants and style factory.

Two-layer color system:
  Layer 1 (Palette): Raw color hex values — what the color IS.
  Layer 2 (Semantic): Purpose-based aliases — what the color MEANS.

To change a specific use case: modify the semantic alias.
To change the base color everywhere: modify the palette value.
"""

from __future__ import annotations

__all__ = ["Theme"]


class Theme:
    """Central color and style definitions for the application.

    Uses a two-layer system: base palette colors and semantic aliases.
    Semantic aliases point to palette colors but can be overridden
    individually when a use case needs a different shade.
    """

    # ══════════════════════════════════════════════════════
    # LAYER 1: PALETTE — Raw colors (What IS it?)
    # ══════════════════════════════════════════════════════

    # Blues (Steam's signature dark blue family)
    STEAM_DARK = "#1b2838"
    STEAM_BLUE = "#2a3f5f"
    STEAM_DEEP = "#171a21"
    STEAM_INFO = "#2a475e"

    # Grays
    GRAY_BORDER = "#3d4450"
    GRAY_MUTED = "#888888"
    GRAY_INPUT = "#32444e"
    GRAY_DARK = "#2b2b2b"
    GRAY_SEPARATOR = "#555555"

    # Accent colors
    BLUE = "#4a9eff"
    BLUE_LIGHT = "#5ab0ff"
    GREEN = "#4caf50"
    STEAM_GREEN = "#5c7e10"
    STEAM_GREEN_HOVER = "#699d11"
    RED = "#c75450"
    RED_LIGHT = "#d66460"
    YELLOW = "#FDE100"
    ORANGE = "#FFA500"

    # ProtonDB tier colors (official ProtonDB palette)
    PROTON_PLATINUM = "#B4C7D9"
    PROTON_GOLD = "#FDE100"
    PROTON_SILVER = "#C0C0C0"
    PROTON_BRONZE = "#CD7F32"
    PROTON_NATIVE = "#5CB85C"
    PROTON_BORKED = "#D9534F"
    PROTON_PENDING = "#1C39BB"
    PROTON_UNKNOWN = "#FE28A2"

    # Steam Deck status colors
    DECK_VERIFIED = "#59BF40"
    DECK_PLAYABLE = "#FDE100"
    DECK_UNSUPPORTED = "#D9534F"
    DECK_UNKNOWN = "#808080"

    # Text
    TEXT_LIGHT = "#c7d5e0"
    TEXT_WHITE = "#ffffff"
    TEXT_DARK = "#e0e0e0"

    # ══════════════════════════════════════════════════════
    # LAYER 2: SEMANTIC — Purpose-based aliases (What MEANS it?)
    # ══════════════════════════════════════════════════════

    # Backgrounds
    BG_PRIMARY = STEAM_DARK
    BG_SECONDARY = STEAM_BLUE
    BG_DARK = STEAM_DEEP
    BG_INFO_BOX = STEAM_INFO
    BG_INPUT = GRAY_INPUT
    BG_WIDGET = GRAY_DARK

    # Borders
    BORDER = GRAY_BORDER
    BORDER_SEPARATOR = GRAY_SEPARATOR

    # Actions
    ACCENT = BLUE
    ACCENT_HOVER = BLUE_LIGHT
    DANGER = RED
    DANGER_HOVER = RED_LIGHT
    SUCCESS = GREEN
    WARNING = YELLOW

    # Text
    TEXT_PRIMARY = TEXT_LIGHT
    TEXT_MUTED = GRAY_MUTED

    # Feature-specific (easy to change independently!)
    ACHIEVEMENT_GOLD = YELLOW
    PEGI_HOVER = YELLOW
    MODIFIED_FIELD_BG = "#3a2a00"
    MODIFIED_FIELD_BORDER = ORANGE
    CATEGORY_SELECTED = "#FFD700"
    LOGIN_BUTTON = STEAM_GREEN
    LOGIN_BUTTON_HOVER = STEAM_GREEN_HOVER

    # ProtonDB tier aliases (change individually if needed!)
    PROTONDB_PLATINUM = PROTON_PLATINUM
    PROTONDB_GOLD = PROTON_GOLD
    PROTONDB_SILVER = PROTON_SILVER
    PROTONDB_BRONZE = PROTON_BRONZE
    PROTONDB_NATIVE = PROTON_NATIVE
    PROTONDB_BORKED = PROTON_BORKED
    PROTONDB_PENDING = PROTON_PENDING
    PROTONDB_UNKNOWN = PROTON_UNKNOWN

    # Steam Deck status aliases
    STEAMDECK_VERIFIED = DECK_VERIFIED
    STEAMDECK_PLAYABLE = DECK_PLAYABLE
    STEAMDECK_UNSUPPORTED = DECK_UNSUPPORTED
    STEAMDECK_UNKNOWN = DECK_UNKNOWN

    # ══════════════════════════════════════════════════════
    # COLOR DICTS — For lookup by tier/status string
    # ══════════════════════════════════════════════════════

    PROTONDB_COLORS: dict[str, str] = {
        "platinum": PROTON_PLATINUM,
        "gold": PROTON_GOLD,
        "silver": PROTON_SILVER,
        "bronze": PROTON_BRONZE,
        "native": PROTON_NATIVE,
        "borked": PROTON_BORKED,
        "pending": PROTON_PENDING,
        "unknown": PROTON_UNKNOWN,
    }

    STEAMDECK_COLORS: dict[str, str] = {
        "verified": DECK_VERIFIED,
        "playable": DECK_PLAYABLE,
        "unsupported": DECK_UNSUPPORTED,
        "unknown": DECK_UNKNOWN,
    }

    # ══════════════════════════════════════════════════════
    # STYLE FACTORIES — Reusable stylesheet generators
    # ══════════════════════════════════════════════════════

    @staticmethod
    def button_danger() -> str:
        """Stylesheet for danger/destructive action buttons.

        Returns:
            CSS stylesheet string for QPushButton.
        """
        return f"""
            QPushButton {{ background-color: {Theme.DANGER}; color: {Theme.TEXT_WHITE};
                          font-weight: bold; padding: 8px 16px; }}
            QPushButton:hover {{ background-color: {Theme.DANGER_HOVER}; }}
        """

    @staticmethod
    def button_primary() -> str:
        """Stylesheet for primary action buttons.

        Returns:
            CSS stylesheet string for QPushButton.
        """
        return f"""
            QPushButton {{ background-color: {Theme.ACCENT}; color: {Theme.TEXT_WHITE};
                          padding: 8px 16px; }}
            QPushButton:hover {{ background-color: {Theme.ACCENT_HOVER}; }}
        """

    @staticmethod
    def button_steam() -> str:
        """Stylesheet for Steam-green action buttons (login etc).

        Returns:
            CSS stylesheet string for QPushButton.
        """
        return f"""
            QPushButton {{ background-color: {Theme.LOGIN_BUTTON}; color: {Theme.TEXT_WHITE};
                          border: none; padding: 10px 20px; border-radius: 3px;
                          font-weight: bold; }}
            QPushButton:hover {{ background-color: {Theme.LOGIN_BUTTON_HOVER}; }}
        """

    @staticmethod
    def progress_bar() -> str:
        """Stylesheet for progress bars.

        Returns:
            CSS stylesheet string for QProgressBar.
        """
        return f"""
            QProgressBar {{ border: 1px solid {Theme.BORDER_SEPARATOR}; border-radius: 5px;
                          text-align: center; background: {Theme.BG_WIDGET}; }}
            QProgressBar::chunk {{ background: {Theme.ACCENT}; border-radius: 4px; }}
        """

    @staticmethod
    def info_box() -> str:
        """Stylesheet for informational text boxes.

        Returns:
            CSS stylesheet string for QLabel.
        """
        return f"""
            QLabel {{ background-color: {Theme.BG_INFO_BOX}; padding: 15px;
                    border-radius: 5px; color: {Theme.TEXT_PRIMARY}; }}
        """

    @staticmethod
    def pegi_button() -> str:
        """Stylesheet for PEGI rating icon buttons.

        Returns:
            CSS stylesheet string for QPushButton.
        """
        return f"""
            QPushButton {{ border: 2px solid {Theme.BORDER}; background-color: {Theme.BG_PRIMARY};
                          border-radius: 4px; }}
            QPushButton:hover {{ border: 2px solid {Theme.PEGI_HOVER};
                               background-color: {Theme.BG_SECONDARY}; }}
            QPushButton:pressed {{ background-color: #1a2332; }}
        """

    @staticmethod
    def modified_field() -> str:
        """Stylesheet for metadata fields that have been modified.

        Returns:
            CSS stylesheet string for QLineEdit.
        """
        return f"border: 2px solid {Theme.MODIFIED_FIELD_BORDER};"

    # ------------------------------------------------------------------
    # Style constants for consistent UI (replacements happen in separate task)
    # ------------------------------------------------------------------
    STYLE_HINT = "color: gray; font-style: italic;"
    STYLE_WARNING = "color: orange;"
    STYLE_SUCCESS = "color: green; font-weight: bold;"
    STYLE_ERROR = "color: red; font-weight: bold;"
    STYLE_SECTION_HEADER = "font-size: 14px; font-weight: bold;"
    STYLE_PROGRESS_BAR = """
        QProgressBar {
            border: 1px solid #555;
            border-radius: 5px;
            background: #2b2b2b;
        }
        QProgressBar::chunk {
            background: #4a9eff;
            border-radius: 4px;
        }
    """
