#
# steam_library_manager/ui/theme.py
# Colors, fonts and stylesheet helpers for the UI
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

__all__ = ["Theme"]


class Theme:
    # -- base palette --

    # steam's dark blue family
    STEAM_DARK = "#1b2838"
    STEAM_BLUE = "#2a3f5f"
    STEAM_DEEP = "#171a21"
    STEAM_INFO = "#2a475e"

    # grays
    GRAY_BORDER = "#3d4450"
    GRAY_MUTED = "#888888"
    GRAY_INPUT = "#32444e"
    GRAY_DARK = "#2b2b2b"
    GRAY_SEP = "#555555"

    # accents
    BLUE = "#4a9eff"
    BLUE_LT = "#5ab0ff"
    GRN = "#4caf50"
    STEAM_GRN = "#5c7e10"
    STEAM_GRN_HVR = "#699d11"
    RED = "#c75450"
    RED_LT = "#d66460"
    YELLOW = "#FDE100"
    ORANGE = "#FFA500"

    # protondb tier colors
    # FDE100 = BVB 09 Dortmund yellow - had to pick my club's color for gold!
    # 1C39BB = Persian Blue, FE28A2 = Persian Rose
    # found both on color-hex.com while browsing palettes, couldn't resist
    PDB_PLATIN = "#B4C7D9"
    PDB_GOLD = "#FDE100"
    PDB_SILVER = "#C0C0C0"
    PDB_BRONZE = "#CD7F32"
    PDB_NATIVE = "#5CB85C"
    PDB_BORKED = "#D9534F"
    PDB_PENDING = "#1C39BB"
    PDB_UNK = "#FE28A2"

    # deck compat status
    DECK_OK = "#59BF40"
    DECK_PLAY = "#FDE100"
    DECK_UNSUP = "#D9534F"
    DECK_UNK = "#808080"

    # txt colors
    TXT_LIGHT = "#c7d5e0"
    TXT_WHITE = "#ffffff"
    TXT_DARK = "#e0e0e0"

    # -- semantic aliases --

    BG_PRI = STEAM_DARK
    BG_SEC = STEAM_BLUE
    BG_DARK = STEAM_DEEP
    BG_INFO = STEAM_INFO
    BG_INPUT = GRAY_INPUT
    BG_WIDGET = GRAY_DARK

    BORDER = GRAY_BORDER
    BORDER_SEP = GRAY_SEP

    ACCENT = BLUE
    ACCENT_HVR = BLUE_LT
    DANGER = RED
    DANGER_HVR = RED_LT
    SUCCESS = GRN
    WARNING = YELLOW

    TXT_PRI = TXT_LIGHT
    TXT_MUTED = GRAY_MUTED

    # feature stuff
    ACHV_GOLD = YELLOW
    PEGI_HVR = YELLOW
    MOD_BG = "#3a2a00"
    MOD_BORDER = ORANGE
    CAT_SEL = "#FFD700"
    LOGIN_BTN = STEAM_GRN
    LOGIN_BTN_HVR = STEAM_GRN_HVR

    # lookup dicts for tier/status coloring
    PDB_COLORS = {
        "platinum": PDB_PLATIN,
        "gold": PDB_GOLD,
        "silver": PDB_SILVER,
        "bronze": PDB_BRONZE,
        "native": PDB_NATIVE,
        "borked": PDB_BORKED,
        "pending": PDB_PENDING,
        "unknown": PDB_UNK,
    }

    DECK_COLORS = {
        "verified": DECK_OK,
        "playable": DECK_PLAY,
        "unsupported": DECK_UNSUP,
        "unknown": DECK_UNK,
    }

    # -- qss factories --

    @staticmethod
    def btn_danger():
        # red destroy btn
        return f"""
            QPushButton {{ background-color: {Theme.DANGER}; color: {Theme.TXT_WHITE};
                          font-weight: bold; padding: 8px 16px; }}
            QPushButton:hover {{ background-color: {Theme.DANGER_HVR}; }}
        """

    @staticmethod
    def btn_primary():
        return f"""
            QPushButton {{ background-color: {Theme.ACCENT}; color: {Theme.TXT_WHITE};
                          padding: 8px 16px; }}
            QPushButton:hover {{ background-color: {Theme.ACCENT_HVR}; }}
        """

    @staticmethod
    def btn_steam():
        # steam green login btn
        return f"""
            QPushButton {{ background-color: {Theme.LOGIN_BTN}; color: {Theme.TXT_WHITE};
                          border: none; padding: 10px 20px; border-radius: 3px;
                          font-weight: bold; }}
            QPushButton:hover {{ background-color: {Theme.LOGIN_BTN_HVR}; }}
        """

    @staticmethod
    def progressbar_style():
        return f"""
            QProgressBar {{ border: 1px solid {Theme.BORDER_SEP}; border-radius: 5px;
                          text-align: center; background: {Theme.BG_WIDGET}; }}
            QProgressBar::chunk {{ background: {Theme.ACCENT}; border-radius: 4px; }}
        """

    @staticmethod
    def info_box():
        return f"""
            QLabel {{ background-color: {Theme.BG_INFO}; padding: 15px;
                    border-radius: 5px; color: {Theme.TXT_PRI}; }}
        """

    @staticmethod
    def pegi_btn():
        return f"""
            QPushButton {{ border: 2px solid {Theme.BORDER}; background-color: {Theme.BG_PRI};
                          border-radius: 4px; }}
            QPushButton:hover {{ border: 2px solid {Theme.PEGI_HVR};
                               background-color: {Theme.BG_SEC}; }}
            QPushButton:pressed {{ background-color: #1a2332; }}
        """

    @staticmethod
    def mod_field():
        return "border: 2px solid %s;" % Theme.MOD_BORDER

    # inline styles
    STYLE_HINT = "color: gray; font-style: italic;"
    STYLE_WARN = "color: orange;"
    STYLE_OK = "color: green; font-weight: bold;"
    STYLE_ERR = "color: red; font-weight: bold;"
    STYLE_HDR = "font-size: 14px; font-weight: bold;"
