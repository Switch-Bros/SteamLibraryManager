#
# steam_library_manager/utils/timeouts.py
# All the timeout/delay constants in one place
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

"""Central timeout and delay constants used across the app.

Network, database, thread timeouts listed here
No magic numbers scattered everywhere. Values are in seconds unless the name says _MS (milliseconds).

HTTP_TIMEOUT_SCRAPE is a tuple (connect, read) for requests that
need a longer read timeout (aka scraping full profile pages).
"""

from __future__ import annotations

HTTP_TIMEOUT_SHORT = 5
HTTP_TIMEOUT = 10
HTTP_TIMEOUT_LONG = 15
HTTP_TIMEOUT_API = 30
HTTP_TIMEOUT_SCRAPE = (10, 60)

DB_CONNECT_TIMEOUT = 30
DB_BUSY_TIMEOUT_MS = 30_000

THREAD_WAIT_MS = 3000
THREAD_WAIT_LONG_MS = 5000
