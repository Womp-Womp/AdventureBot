# src/utils/config.py
"""
Configuration loader for the Lore Weaver bot.

This module loads essential configuration variables from a .env file
at the root of the project directory. It uses the `python-dotenv` library
to achieve this. The loaded variables are made available as module-level
constants.

Required environment variables:
    DISCORD_TOKEN: The Discord bot token.
    GEMINI_API_KEY: The API key for Google's Gemini service.
    ADMIN_USER_ID: The Discord User ID of the bot administrator.

Upon import, this module attempts to load these variables. If critical
variables like DISCORD_TOKEN or GEMINI_API_KEY are missing, the bot's
main module (`src/main.py`) is expected to handle this by logging an
error and exiting.
"""
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Attempt to load environment variables from a .env file
# This should be called as early as possible, ideally once when the config module is imported.
if load_dotenv():
    logger.debug(".env file loaded successfully.")
else:
    logger.debug("No .env file found or it is empty. Relying on environment variables set externally if any.")

# --- Core Bot Configuration ---
DISCORD_TOKEN: str | None = os.getenv("DISCORD_TOKEN")
"""The Discord Bot Token obtained from the Discord Developer Portal."""

GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
"""The API Key for accessing Google's Gemini services."""

ADMIN_USER_ID: str | None = os.getenv("ADMIN_USER_ID")
"""The Discord User ID of the primary administrator for the bot.
Used for restricting access to sensitive commands."""


# --- Sanity Checks on Load (Optional, main.py handles critical exits) ---
# These logs help during startup to see if configs are picked up.
if not DISCORD_TOKEN:
    logger.warning("DISCORD_TOKEN is not set in environment variables or .env file.")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is not set in environment variables or .env file.")
if not ADMIN_USER_ID:
    logger.warning("ADMIN_USER_ID is not set in environment variables or .env file. Admin commands will not be restricted by default.")


if __name__ == '__main__':
    # This block allows testing the configuration loading directly.
    # It sets up basic logging just for this test run.
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                        handlers=[logging.StreamHandler()])

    logger.info("--- Configuration Loading Test ---")
    if DISCORD_TOKEN:
        logger.info(f"DISCORD_TOKEN: Loaded (length: {len(DISCORD_TOKEN)})")
    else:
        logger.info("DISCORD_TOKEN: Not found or empty.")

    if GEMINI_API_KEY:
        logger.info(f"GEMINI_API_KEY: Loaded (length: {len(GEMINI_API_KEY)})")
    else:
        logger.info("GEMINI_API_KEY: Not found or empty.")

    if ADMIN_USER_ID:
        logger.info(f"ADMIN_USER_ID: {ADMIN_USER_ID}")
    else:
        logger.info("ADMIN_USER_ID: Not found or empty.")

    logger.info("\n--- Instructions ---")
    logger.info("Ensure you have a .env file in the root directory with the following content:")
    logger.info("DISCORD_TOKEN=your_discord_bot_token_here")
    logger.info("GEMINI_API_KEY=your_google_ai_studio_api_key_here")
    logger.info("ADMIN_USER_ID=your_personal_discord_user_id_here")
    logger.info("\nIf you just created it, you might need to restart your Python environment for changes to take effect if run via an IDE or some execution environments.")
    logger.info("If running with systemd or Docker, ensure environment variables are passed correctly there.")
