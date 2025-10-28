"""
Configuration module for Hermes Bot.

Loads and validates environment variables required for the bot to function.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Required configuration
OVERSEERR_API_KEY = os.getenv("OVERSEERR_API_KEY")
OVERSEERR_BASE_URL = os.getenv("OVERSEERR_BASE_URL", "http://localhost:5055/api/v1")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Optional configuration with defaults
VERIFICATION_EXPIRY_MINUTES = int(os.getenv("VERIFICATION_EXPIRY_MINUTES", "15"))
ALLOW_GUILD_COMMANDS = os.getenv("ALLOW_GUILD_COMMANDS", "false").lower() in ("true", "1", "yes")

# Validate required variables
if not OVERSEERR_API_KEY:
    raise ValueError("OVERSEERR_API_KEY environment variable is required")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

if not OVERSEERR_BASE_URL:
    raise ValueError("OVERSEERR_BASE_URL environment variable is required")
