#
# steam_library_manager/utils/timeouts.py
# Central timeout and delay constants for network, DB, and UI operations.
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

# -- Network request timeouts (seconds) --

HTTP_TIMEOUT_SHORT = 5  # quick lookups: account check, reviews, icons
HTTP_TIMEOUT = 10  # standard API/web requests
HTTP_TIMEOUT_LONG = 15  # heavier ops: HLTB detail, curators, API refresh
HTTP_TIMEOUT_API = 30  # bulk Steam Web API calls, HLTB search
HTTP_TIMEOUT_SCRAPE = (10, 60)  # profile scraper (connect, read)

# -- Database timeouts --

DB_CONNECT_TIMEOUT = 30  # sqlite3.connect() timeout in seconds
DB_BUSY_TIMEOUT_MS = 30_000  # PRAGMA busy_timeout in milliseconds

# -- Thread shutdown --

THREAD_WAIT_MS = 3000  # default thread.wait() timeout
THREAD_WAIT_LONG_MS = 5000  # longer wait for heavy workers
