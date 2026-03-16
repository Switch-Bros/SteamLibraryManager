#
# steam_library_manager/services/curator_presets.py
# Built-in list of popular Steam Curators for quick setup
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CuratorPreset", "POPULAR_CURATORS"]


@dataclass(frozen=True)
class CuratorPreset:
    """A well-known Steam Curator entry."""

    curator_id: int
    name: str
    description: str


# Curator IDs verified via live Steam Store HAR-Capture (2026-02-24).
# Source: https://store.steampowered.com/curators/ajaxgetcurators/
# Verified by: HeikesFootSlave (HAR) + Chris (analysis) + Alex (web search).
# Publishers and controversial curators excluded.
POPULAR_CURATORS: tuple[CuratorPreset, ...] = (
    # Tier 1 - Major (100k+ followers)
    CuratorPreset(1850, "PC Gamer", "Major gaming publication"),
    CuratorPreset(6856269, "Just Good PC Games", "Community recommendations"),
    CuratorPreset(4771848, "/r/pcmasterrace Group", "Reddit PC community"),
    CuratorPreset(11284407, "Critiquing Doge", "Community review curator"),
    CuratorPreset(4973374, "RPGWatch", "RPG-focused reviews"),
    CuratorPreset(7871885, "Original Curators Group", "1500+ game reviews"),
    CuratorPreset(6866589, "GameStar", "German gaming magazine"),
    CuratorPreset(35411526, "Wholesome Games", "Family-friendly picks"),
    CuratorPreset(6923402, "Yahtzee Recommends", "Zero Punctuation picks"),
    CuratorPreset(5195189, "GrabTheGames", "Indie game reviews"),
    # Tier 2 - Active reviewers (50k-100k)
    CuratorPreset(35387214, "Metacritic.", "Aggregated review scores"),
    CuratorPreset(8049466, "German_Gamer_Community", "German gaming community"),
    CuratorPreset(6856130, "Rely on Horror", "Horror game specialists"),
    CuratorPreset(11247776, "Co-op Cowboys", "Co-op game recommendations"),
    CuratorPreset(6856127, "Roguelikes", "Roguelike genre picks"),
    CuratorPreset(28625128, "Skill Up Curates...", "In-depth game analysis"),
    CuratorPreset(6866630, "RPG Codex (Official)", "RPG enthusiast reviews"),
    # Tier 3 - Niche / Special Interest
    CuratorPreset(33526, "Rock Paper Shotgun", "PC gaming journalism"),
    CuratorPreset(5280029, "AngryJoeShow", "Passionate game reviews"),
    CuratorPreset(33483305, "Proton Compatible", "Linux/Deck compatibility"),
)
