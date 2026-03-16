#
# steam_library_manager/ui/workers/game_load_worker.py
# Background worker thread for asynchronous game loading.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, pyqtSignal

if TYPE_CHECKING:
    from steam_library_manager.services.game_service import GameService

__all__ = ["GameLoadWorker"]


class GameLoadWorker(QThread):
    """Background thread for loading games without blocking the UI."""

    progress_update = pyqtSignal(str, int, int)
    finished = pyqtSignal(bool)

    def __init__(self, game_service: "GameService", user_id: str):
        super().__init__()
        self.game_service = game_service
        self.user_id = user_id

    def run(self) -> None:

        def progress_callback(step: str, current: int, total: int):
            self.progress_update.emit(step, current, total)

        success = self.game_service.load_and_prepare(self.user_id, progress_callback)
        self.finished.emit(success)
