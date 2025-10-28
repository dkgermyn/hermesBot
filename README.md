# Hermes - Overseerr Discord Link Bot

**Hermes** is a Discord bot that allows Overseerr users to securely self-link their Discord account to their Overseerr account. Once linked, Overseerr can @mention them in its own Discord notifications (e.g., "your request was approved", "your movie is now available") without requiring any external watcher scripts or cron jobs.

## Why Use Hermes?

Overseerr has built-in Discord notification support, but it can only @mention users if their Discord ID is stored in Overseerr's database. Hermes provides a secure, user-friendly way for people to link their own accounts without requiring administrator intervention.

**Key Benefits:**
- Users can do their own Discord<->Overseer linking
- No database access required (only Overseerr API)
- No Plex credentials needed
- Secure proof-of-control verification
- Works entirely through DMs for privacy
- No additional infrastructure (no cron jobs, no watchers)

## Features

- `!link <identifier>` - Start the linking process (identifier can be Plex username, email, or display name)
- `!done` - Complete verification after adding code to Overseerr display name
- `!status` - Check if your Discord account is currently linked
- `!unlink <identifier>` - Remove the Discord link from your Overseerr account
- `!help` - Show help information

**All commands work exclusively via Direct Messages (DMs)** for privacy.

## How It Works

1. **User initiates linking**: DM the bot with `!link YourPlexUsername`
2. **Bot generates verification code**: Bot gives you a one-time code like `[ABCD-1234]`
3. **User proves control**: User temporarily adds the code to their Overseerr Display Name
4. **Bot verifies and links**: User runs `!done`, bot confirms the code is present and saves Discord ID to Overseerr
5. **Overseerr can now @mention**: When Overseerr sends Discord notifications, it uses the stored Discord ID to @mention the user

## Security Model

Hermes follows a minimal-privilege security model:

- Overseerr API key (read user list, write notification settings)
- Discord bot token

**Proof of Control:**
Users prove they control an Overseerr account by temporarily modifying their Display Name to include a verification code. Only someone logged into that Overseerr account can make that change, preventing impersonation.

## Prerequisites

Before running Hermes, you need:

1. **A running Overseerr instance**
   - Accessible from where you'll run the bot
   - API key generated (Overseerr → Settings → General → API Key)

2. **Discord bot token**
   - Create a bot at [Discord Developer Portal](https://discord.com/developers/applications)
   - Enable "Message Content Intent" under Privileged Gateway Intents
   - Fetch the bot's token (you'll need it later)
   - Invite bot to your server with basic permissions (Send Messages, Read Messages, View Channels)

3. **Overseerr Discord notifications configured**
   - Overseerr → Settings → Notifications → Discord
   - Configure your Discord webhook URL
   - **Enable "Enable Mentions"** (this allows Overseerr to use `<@discordId>` syntax)

## Installation

### Option 1: Python

```bash
# Clone the repository
git clone https://github.com/dkgermyn/hermesBot.git
cd hermesBot

# Create and configure environment file
cp .env.example .env
# Edit .env with your credentials

# Install dependencies
pip install -r requirements.txt

# Run the bot
python bot.py
```

### Option 2: Docker

```bash
# Clone the repository
git clone https://github.com/dkgermyn/hermesBot.git
cd hermesBot

# Create and configure environment file
cp .env.example .env
# Edit .env with your credentials

# Build the Docker image
docker build -t hermesbot .

# Run the container
docker run -d --name hermesbot --env-file .env hermesbot
```

### Option 3: Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  hermesbot:
    build: .
    container_name: hermesbot
    env_file: .env
    restart: unless-stopped
```

Then run:
```bash
docker compose up -d
```

## Configuration

Edit `.env` with your credentials:

```bash
# Overseerr Configuration
OVERSEERR_API_KEY=your_overseerr_api_key_here
OVERSEERR_BASE_URL=http://localhost:5055/api/v1 

# Discord Bot Configuration
BOT_TOKEN=your_discord_bot_token_here

# Verification Settings (optional)
VERIFICATION_EXPIRY_MINUTES=15

# Privacy Settings (optional)
ALLOW_GUILD_COMMANDS=false
```

### Configuration Options

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OVERSEERR_API_KEY` | Yes | - | API key from Overseerr (Settings → General) |
| `OVERSEERR_BASE_URL` | Yes | `http://localhost:5055/api/v1` | Base URL for Overseerr API |
| `BOT_TOKEN` | Yes | - | Discord bot token |
| `VERIFICATION_EXPIRY_MINUTES` | No | `15` | How long verification codes remain valid |
| `ALLOW_GUILD_COMMANDS` | No | `false` | Set to `true` to allow commands in guild channels (e.g., #bots). Default is DM-only for privacy. |

## User Guide

### Linking Your Account

1. **Open Discord** and find the bot in your server's member list
2. **Send a Direct Message** to the bot (right-click → Message)
3. **Run the link command**:
   ```
   !link YourPlexUsername
   ```
   *(You can also use your email or Overseerr display name)*

4. **The bot will respond** with a verification code like `[ABCD-1234]`

5. **In Overseerr**, click your profile icon (top-right) → Settings → General

6. **Edit your Display Name** to include the code anywhere:
   ```
   John Doe [ABCD-1234]
   ```

7. **Save** your Overseerr settings

8. **Back in Discord DM**, tell the bot you're done:
   ```
   !done
   ```

9. **Success!** The bot will confirm linking. You can now remove the code from your Overseerr display name.

### Checking Status

```
!status
```

Shows whether you have a pending verification or are already linked.

### Unlinking

```
!unlink YourPlexUsername
```

Removes your Discord ID from Overseerr. You'll stop receiving @mentions.

### Getting Help

```
!help
```

Shows available commands and usage instructions.

## Important Notes

### Privacy
- **By default, Hermes only responds to Direct Messages (DMs)** for privacy. Commands sent in guild channels will be ignored unless you set `ALLOW_GUILD_COMMANDS=true` in your `.env` file.
- If you enable guild commands, consider creating a private #bots channel to keep usernames and codes out of public view.
- Your Plex username and verification codes are kept private in DMs.
- Your Discord ID is only stored in Overseerr (not in any separate database).

### Discord Server Privacy Settings (Required for DMs)
**IMPORTANT:** For users to DM the bot, the Discord server must have the following privacy setting enabled:

1. Go to **Server Settings** → **Privacy Settings**
2. Enable **"Direct Messages / Allow DMs from other members in this server"**

Without this setting enabled, users will not be able to send DMs to the bot.

### Automatic Notification Settings
When you run `!done` to complete linking, Hermes automatically enables Overseerr's "Request Approved" and "Request Available" Discord notifications for you. You can later run `!unlink` to disable them

### Overseerr Display Name
- You can remove the verification code from your display name after successfully linking
- The code is only needed during the verification step
- If you don't complete verification within 15 minutes (default), the code expires

## Troubleshooting

### Bot doesn't respond to commands

**Check:**
- Did you send the command via DM (not in a channel)?
- Is the bot online and running?
- Does the bot have "Message Content Intent" enabled in Discord Developer Portal?

### "Could not find Overseerr account"

**Check:**
- Spelling of your Plex username (case-sensitive)
- Try using your email address instead: `!link user@example.com`
- Verify you have an account in Overseerr

### "Failed to link your accounts due to an API error"

**Check:**
- Is `OVERSEERR_API_KEY` correct in `.env`?
- Is `OVERSEERR_BASE_URL` correct and accessible from where the bot runs?
- Check bot logs for specific error messages

### "Verification code not found in display name"

**Check:**
- Did you save your Overseerr settings after adding the code?
- Did you include the exact code with brackets: `[ABCD-1234]`?
- Is the code still valid (hasn't expired)?

### Overseerr isn't @mentioning me

**Check:**
- Overseerr → Settings → Notifications → Discord → "Enable Mentions" is checked
- You successfully ran `!done` and got a success message
- The Discord webhook is properly configured in Overseerr

## FAQ

### Q: Why do I need to change my Display Name temporarily?

**A:** This proves you control that Overseerr account. Only someone logged into your Overseerr session can modify your display name, so it prevents someone else from linking your account to their Discord.

### Q: Can administrators link people manually?

**A:** Administrators with Overseerr access can manually set Discord IDs in Overseerr's user settings. However, Hermes provides a self-service option so users don't need admin help.

### Q: Does the bot need database access?

**A:** No! Hermes only uses Overseerr's public API. It doesn't need direct database access, Plex access, or any privileged infrastructure access.

### Q: What if I change my Plex username?

**A:** Unlink your old account (`!unlink OldUsername`) then link with your new username (`!link NewUsername`).

### Q: Can one Discord account be linked to multiple Overseerr accounts?

**A:** Technically yes, but Overseerr will only store one Discord ID per Overseerr user. The most recent link will be used for notifications.

### Q: Can one Overseerr account be linked to multiple Discord accounts?

**A:** No. Each Overseerr account can only have one Discord ID. Linking a different Discord account will replace the previous one.

### Q: Is my Discord token or API key logged?

**A:** No. Hermes never logs secrets. It only logs operational events (user linked/unlinked, verification attempts).

### Q: Why does the bot only work in DMs?

**A:** For privacy. This prevents usernames and verification codes from being exposed in public channels.

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Karl Germyn

## Support

- **Issues**: [GitHub Issues](https://github.com/dkgermyn/hermesBot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dkgermyn/hermesBot/discussions)

## Acknowledgments

- Built with [discord.py](https://github.com/Rapptz/discord.py)
- Designed for [Overseerr](https://github.com/sct/overseerr)

---

**Note:** This bot does not store any user data. All information is stored in Overseerr via its API. The bot only maintains temporary verification codes in memory for the linking process.
