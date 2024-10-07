"""
__init__.py

Version: 1.3.0

This module serves as the initializer for the bot package, aggregating all
submodules for easier importing. It imports essential functionalities from
the info, snapshots, utils, and verify modules to provide a unified interface
for the bot.

Usage:
    - Import all functions directly from the bot package:
      `import bot_modules`.

Modules Included:
    - info: Functions for handling info commands related to the bot.
    - snapshots: Functions for managing Minecraft world snapshots.
    - utils: Miscellaneous utility functions used across the bot.
    - verify: Functions for verifying user accounts with the Minecraft server.

Notes:
    - This file does not contain any executable code itself; it only
      facilitates module imports and suppresses linter warnings for unused imports.
"""


# Importing modules
from .info import info, info_snapshots
from .snapshots import create_snapshot, delete_snapshot, download_snapshot, list_snapshots, restore_snapshot
from .utils import get_public_ip, ping
from .verify import verify

# Suppress unused import warnings
__all__ = ['create_snapshot', 'list_snapshots', 'delete_snapshot',
           'restore_snapshot', 'download_snapshot', 'verify', 'get_public_ip',
           'info', 'info_snapshots', 'ping']
