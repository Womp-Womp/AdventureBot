# src/main.py
"""
Main entry point for the Lore Weaver Discord Bot.

This script performs the following actions:
1.  Sets up centralized logging for the application.
2.  Loads configuration from environment variables via `src.utils.config`.
3.  Performs critical configuration checks (e.g., for Discord token, API keys).
4.  Initializes the database connection using `src.core.database`.
5.  Sets up Discord bot intents and creates the `discord.Bot` instance.
6.  Attaches the database connection to the bot instance for access by cogs.
7.  Loads specified cogs (extensions) from `src.bot.cogs`.
8.  Defines an `on_ready` event handler to log bot login status.
9.  Includes a basic example slash command (`/hello`).
10. Runs the bot and handles graceful shutdown of the database connection.
"""
import discord
import os # For potential future use, not strictly necessary for this minimal version
import logging

# --- Logging Setup ---
# Configure basic logging. This will apply to all loggers unless they are
# individually configured otherwise.
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s - [%(funcName)s] %(message)s', # Added funcName
                    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__) # Logger for this specific module


# Custom modules
from src.utils import config # Loads .env variables upon import
from src.core import database

# --- Configuration Check ---
# Ensure critical configurations are present before proceeding.
if not config.DISCORD_TOKEN:
    logger.critical("DISCORD_TOKEN is not set. Please check your .env file.")
    exit()
if not config.GEMINI_API_KEY:
    logger.critical("GEMINI_API_KEY is not set. Please check your .env file.")
    # For now, we might allow the bot to run without Gemini for basic command testing,
    # but actual adventure features will fail.
    # For MVP, it's critical. Let's make it exit.
    exit()
if not config.ADMIN_USER_ID:
    logger.warning("ADMIN_USER_ID is not set. Admin commands will not be restricted.")
    # This is a warning, not critical for bot startup.

# --- Database Initialization ---
db_connection = None # Initialize to None for cleanup check
try:
    # Assuming init_db will be modified to use logging internally
    db_connection = database.init_db()
    logger.info("Database connection process initiated by main.py.") # Clarified who initiates
except Exception as e:
    logger.critical(f"Failed to initialize database in main.py: {e}", exc_info=True)
    exit()

# --- Bot Setup ---
# Define intents required by the bot.
# `message_content` is needed if reading message content (e.g., for prefix commands or specific message parsing).
# `members` might be needed for accessing member details beyond what's available in an interaction context.
intents = discord.Intents.default()
intents.message_content = True
# intents.members = True

bot = discord.Bot(intents=intents) # Using discord.Bot for application commands (slash commands primarily)

# Make the database connection available to cogs via the bot instance.
# This is a common pattern for sharing resources with extensions.
bot.db_connection = db_connection

# --- Cog Loading ---
# Define the initial extensions (cogs) to be loaded when the bot starts.
# Paths are dot-separated, relative to the project root (where Python is run from).
INITIAL_EXTENSIONS = [
    'src.bot.cogs.adventure'
]

@bot.event
async def on_ready():
    """
    Event handler called when the bot has successfully connected to Discord
    and is ready to operate.
    """
    logger.info(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    logger.info('Bot is ready and online!')
    logger.info('------ guilds: %s ------', len(bot.guilds)) # Log guild count
    # You can set a custom status here if desired
    # await bot.change_presence(activity=discord.Game(name="/start_adventure or /hello"))

# --- Basic Slash Command Example (Optional, for testing bot responsiveness) ---
@bot.slash_command(name="hello", description="Replies with a friendly greeting from Lore Weaver.")
async def hello(ctx: discord.ApplicationContext):
    """A simple slash command to confirm the bot is responsive."""
    logger.info(f"/hello command invoked by {ctx.author.name} (ID: {ctx.author.id}) in guild {ctx.guild_id}.")
    await ctx.respond(f"Hello {ctx.author.mention}! I am Lore Weaver, ready to weave some tales with you.")

# --- Main Execution Block ---
if __name__ == "__main__":
    logger.info("Attempting to start Lore Weaver bot...")

    # Load all specified extensions (cogs)
    if INITIAL_EXTENSIONS:
        logger.info(f"Loading {len(INITIAL_EXTENSIONS)} initial extension(s)...")
        for extension_path in INITIAL_EXTENSIONS:
            try:
                bot.load_extension(extension_path)
                logger.info(f"Successfully loaded extension: {extension_path}")
            except discord.DiscordException as e: # More specific exception for discord related issues
                logger.error(f"Failed to load extension {extension_path}: {e.__class__.__name__} - {e}", exc_info=True)
            except Exception as e: # Catch any other non-Discord exception during loading
                logger.error(f"An unexpected error occurred while loading extension {extension_path}: {e}", exc_info=True)
    else:
        logger.info("No initial extensions (cogs) defined to load.")

    try:
        # Start the bot using the token from config.
        # This is a blocking call until the bot is stopped.
        bot.run(config.DISCORD_TOKEN)
    except discord.LoginFailure:
        logger.critical("CRITICAL: Bot login failed. This is likely due to an invalid DISCORD_TOKEN. Please check your .env file or environment variables.", exc_info=True)
    except TypeError as e: # To catch the "token must be of type str" if DISCORD_TOKEN is None
        logger.critical(f"CRITICAL: TypeError during bot run, likely DISCORD_TOKEN is None: {e}", exc_info=True)
    except Exception as e:
        logger.critical(f"CRITICAL: An unexpected error occurred while trying to run the bot: {e}", exc_info=True)
    finally:
        # --- Cleanup (runs after bot stops or if an error occurs during run) ---
        # Ensures resources like the database connection are properly closed.
        if db_connection:
            try:
                db_connection.close()
                logger.info("Database connection closed successfully.")
            except Exception as e:
                logger.error(f"Error closing database connection during shutdown: {e}", exc_info=True)
        logger.info("Lore Weaver bot has shut down.")
