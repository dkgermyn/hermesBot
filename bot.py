"""
Hermes - Overseerr Discord Link Bot

A Discord bot that allows Overseerr users to self-link their Discord account
to their Overseerr account, enabling @mentions in Overseerr's Discord notifications.

By default, the bot only responds to Direct Messages (DMs) for privacy.
Set ALLOW_GUILD_COMMANDS=true in .env to allow commands in guild channels.
"""

import logging
import asyncio
import time
import string
import random
from typing import Dict

import discord
from discord.ext import commands

import config
from overseerr_api import find_user, find_user_by_discord_id, update_user_notifications

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('hermes-bot')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# In-memory storage for pending link requests
# Structure: {discord_id: {"identifier": str, "code": str, "ts": float, "user_id": int}}
pending_links: Dict[int, Dict] = {}


def generate_verification_code() -> str:
    """Generate a random verification code (e.g., ABCD-1234)."""
    part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{part1}-{part2}"


def cleanup_expired_codes():
    """Remove expired verification codes from pending_links."""
    current_time = time.time()
    expiry_seconds = config.VERIFICATION_EXPIRY_MINUTES * 60

    expired_ids = [
        discord_id for discord_id, data in pending_links.items()
        if current_time - data['ts'] > expiry_seconds
    ]

    for discord_id in expired_ids:
        del pending_links[discord_id]
        logger.info(f"Cleaned up expired verification code for Discord ID {discord_id}")


async def cleanup_task():
    """Background task to periodically clean up expired verification codes."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        cleanup_expired_codes()
        await asyncio.sleep(60)  # Run every minute


def _channel_allowed(ctx):
    """
    Check if commands are allowed in this channel.

    Always allows DMs. In guild channels, checks ALLOW_GUILD_COMMANDS setting.
    """
    # Always allow commands in DM (ctx.guild is None)
    if ctx.guild is None:
        return True
    # In guild channels, only allow if ALLOW_GUILD_COMMANDS is True
    return config.ALLOW_GUILD_COMMANDS


@bot.event
async def setup_hook():
    """Setup hook to initialize background tasks before bot starts."""
    bot.loop.create_task(cleanup_task())
    logger.info("Background cleanup task started")


@bot.event
async def on_ready():
    """Event handler for when the bot is ready."""
    logger.info(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    logger.info(f'Connected to {len(bot.guilds)} guild(s)')
    if config.ALLOW_GUILD_COMMANDS:
        logger.info('Bot is ready to accept commands (DMs and guild channels)')
    else:
        logger.info('Bot is ready to accept commands (DMs ONLY)')


@bot.command(name='help')
async def help_command(ctx):
    """Show help information for Hermes."""
    if not _channel_allowed(ctx):
        await ctx.reply("For privacy, please DM me this command instead.")
        return

    help_text = """**Hermes - Overseerr Discord Link Bot**

Link your Discord account to Overseerr so you can be @mentioned in notifications!

**Commands:**

`!link <identifier>` - Start linking your Discord to your Overseerr account
  (identifier can be your Plex username, email, or display name)

`!done` - Complete the verification after adding the code to your Overseerr display name

`!status` - Check if your Discord account is linked to Overseerr

`!unlink <identifier>` - Remove the link between your Discord and Overseerr

`!help` - Show this help message

**How to Link:**
1. DM me: `!link YourUsername`
2. I'll give you a verification code like [ABCD-1234]
3. In Overseerr, edit your Display Name to include that code
4. Come back here and type `!done`

**Privacy:**
All commands must be sent via DM. Your Discord ID is only stored in Overseerr so Overseerr can @mention you when your requests are approved or available.

**Questions?** See the bot's README or contact your server administrator.
"""
    await ctx.send(help_text)


@bot.command(name='link')
async def link_account(ctx, identifier: str = None):
    """
    Create a verification request to link Discord and Overseerr accounts.

    Usage: !link <identifier>
    Example: !link YourPlexUsername
    """
    if not _channel_allowed(ctx):
        await ctx.reply("For privacy, please DM me this command instead.")
        return

    if not identifier:
        await ctx.send("Usage: `!link <identifier>`\nExample: `!link YourPlexUsername`\n\n"
                      "The identifier can be your Plex username, email, or Overseerr display name.")
        return

    discord_id = ctx.author.id

    # Clean up expired codes before processing
    cleanup_expired_codes()

    # Check if user already has a pending link
    if discord_id in pending_links:
        old_code = pending_links[discord_id]['code']
        await ctx.send(
            f"You already have a pending verification for `{pending_links[discord_id]['identifier']}`.\n"
            f"Use the existing code `{old_code}` or wait {config.VERIFICATION_EXPIRY_MINUTES} minutes for it to expire."
        )
        return

    # Find the user in Overseerr
    user = find_user(identifier)
    if not user:
        await ctx.send(
            f"Could not find an Overseerr account matching `{identifier}`.\n"
            f"Please check the spelling and try again. You can use your Plex username, email, or display name."
        )
        return

    # Check if this Overseerr account is already linked to a Discord ID
    existing_discord_id = user.get('settings', {}).get('notifications', {}).get('discordId')
    if existing_discord_id:
        if existing_discord_id == str(discord_id):
            await ctx.send(f"Your Overseerr account `{identifier}` is already linked to your Discord account!")
            return
        else:
            await ctx.send(
                f"The Overseerr account `{identifier}` is already linked to a different Discord account.\n"
                f"If this is your account, please unlink it first using `!unlink {identifier}`."
            )
            return

    # Generate verification code and store pending request
    verification_code = generate_verification_code()
    pending_links[discord_id] = {
        "identifier": identifier,
        "code": verification_code,
        "ts": time.time(),
        "user_id": user['id']
    }

    logger.info(f"Created link request for Discord ID {discord_id} -> Overseerr user {identifier} (code: {verification_code})")

    await ctx.send(
        f"**Verification started for `{identifier}`**\n\n"
        f"To verify you control this Overseerr account:\n\n"
        f"1. Open Overseerr and click your profile icon (top-right)\n"
        f"2. Go to **Settings** → **General**\n"
        f"3. Change your **Display Name** to include: `[{verification_code}]`\n"
        f"   (You can put it anywhere in your display name)\n"
        f"4. **Save** your settings\n"
        f"5. Return here and type: `!done`\n\n"
        f"This code expires in {config.VERIFICATION_EXPIRY_MINUTES} minutes."
    )


@bot.command(name='done')
async def complete_linking(ctx):
    """
    Complete the verification and link Discord to Overseerr account.

    Usage: !done
    """
    if not _channel_allowed(ctx):
        await ctx.reply("For privacy, please DM me this command instead.")
        return

    discord_id = ctx.author.id

    # Clean up expired codes
    cleanup_expired_codes()

    # Check if user has a pending link request
    if discord_id not in pending_links:
        await ctx.send(
            "You don't have a pending verification request.\n"
            "Start by using `!link <identifier>`"
        )
        return

    pending = pending_links[discord_id]
    identifier = pending['identifier']
    verification_code = pending['code']
    user_id = pending['user_id']

    # Fetch the user from Overseerr to check their display name
    user = find_user(identifier)
    if not user:
        await ctx.send(
            f"Could not find Overseerr account `{identifier}`. Please try again with `!link`."
        )
        del pending_links[discord_id]
        return

    display_name = user.get('displayName', '')

    # Check if the verification code is in the display name
    if verification_code not in display_name:
        await ctx.send(
            f"❌ Verification code `{verification_code}` not found in your Overseerr display name.\n"
            f"Current display name: `{display_name}`\n\n"
            f"Please add `[{verification_code}]` to your display name and try `!done` again."
        )
        return

    # Verification successful - update Discord ID in Overseerr
    if update_user_notifications(user_id, str(discord_id), enable=True):
        await ctx.send(
            f"✅ **Success!** Your Overseerr account `{identifier}` is now linked to your Discord account.\n\n"
            f"Overseerr will now @mention you in Discord when:\n"
            f"• Your requests are approved\n"
            f"• Requested media is available\n"
            f"• Other request notifications occur\n\n"
            f"You can now remove `[{verification_code}]` from your Overseerr display name."
        )

        # Clean up pending request
        del pending_links[discord_id]
    else:
        await ctx.send(
            "❌ Failed to link your accounts due to an API error.\n"
            "Please try again later or contact an administrator."
        )


@bot.command(name='unlink')
async def unlink_account(ctx, identifier: str = None):
    """
    Remove the Discord ID link from your Overseerr account.

    Usage: !unlink <identifier>
    """
    if not _channel_allowed(ctx):
        await ctx.reply("For privacy, please DM me this command instead.")
        return

    if not identifier:
        # Try to find by Discord ID if no identifier provided
        discord_id = str(ctx.author.id)
        user = find_user_by_discord_id(discord_id)

        if not user:
            await ctx.send(
                "Usage: `!unlink <identifier>`\n\n"
                "Your Discord account is not currently linked to any Overseerr account."
            )
            return

        identifier = user.get('plexUsername', 'Unknown')
    else:
        # Find user by provided identifier
        user = find_user(identifier)
        if not user:
            await ctx.send(
                f"Could not find Overseerr account matching `{identifier}`.\n"
                f"Please check the spelling and try again."
            )
            return

        # Verify this user is linked to the caller's Discord ID
        linked_discord_id = user.get('settings', {}).get('notifications', {}).get('discordId')
        if linked_discord_id != str(ctx.author.id):
            await ctx.send(
                f"The Overseerr account `{identifier}` is not linked to your Discord account.\n"
                f"You can only unlink your own account."
            )
            return

    user_id = user['id']

    # Remove the Discord ID
    if update_user_notifications(user_id, None, enable=False):
        await ctx.send(
            f"🔓 **Unlinked successfully!**\n\n"
            f"Your Overseerr account `{identifier}` is no longer linked to Discord.\n"
            f"Overseerr will no longer @mention you in notifications.\n\n"
            f"You can re-link anytime with `!link <identifier>`"
        )
        logger.info(f"Unlinked Discord ID {ctx.author.id} from Overseerr user {identifier}")
    else:
        await ctx.send(
            "❌ Failed to unlink your account due to an API error.\n"
            "Please try again later or contact an administrator."
        )


@bot.command(name='status')
async def check_status(ctx):
    """
    Check if your Discord account is currently linked to Overseerr.

    Usage: !status
    """
    if not _channel_allowed(ctx):
        await ctx.reply("For privacy, please DM me this command instead.")
        return

    discord_id = str(ctx.author.id)

    # Check if user has a pending link
    if ctx.author.id in pending_links:
        pending = pending_links[ctx.author.id]
        await ctx.send(
            f"📋 **Pending Verification**\n\n"
            f"Identifier: `{pending['identifier']}`\n"
            f"Verification Code: `{pending['code']}`\n"
            f"Expires in: ~{config.VERIFICATION_EXPIRY_MINUTES} minutes\n\n"
            f"Complete verification with `!done`"
        )
        return

    # Check if user is already linked
    user = find_user_by_discord_id(discord_id)
    if user:
        identifier = user.get('plexUsername') or user.get('email') or 'Unknown'
        await ctx.send(
            f"✅ **Linked**\n\n"
            f"Your Discord account is linked to Overseerr account: `{identifier}`\n"
            f"You will receive @mentions in Overseerr notifications.\n\n"
            f"To unlink, use `!unlink <identifier>`"
        )
    else:
        await ctx.send(
            f"❌ **Not Linked**\n\n"
            f"Your Discord account is not linked to any Overseerr account.\n"
            f"To link, use `!link <identifier>`"
        )


if __name__ == "__main__":
    logger.info("Starting Hermes (Overseerr Discord Link Bot)")
    logger.info(f"Overseerr API URL: {config.OVERSEERR_BASE_URL}")
    logger.info(f"Verification code expiry: {config.VERIFICATION_EXPIRY_MINUTES} minutes")
    if config.ALLOW_GUILD_COMMANDS:
        logger.info("Privacy mode: Commands allowed in DMs and guild channels")
    else:
        logger.info("Privacy mode: Commands allowed in DMs ONLY")

    # Run the bot (background task starts via setup_hook)
    try:
        bot.run(config.BOT_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise
