"""
Overseerr API interaction module.

Provides functions to interact with the Overseerr API for user management
and notification settings.
"""

import logging
from typing import Optional, List, Dict
import requests

from config import OVERSEERR_API_KEY, OVERSEERR_BASE_URL

logger = logging.getLogger(__name__)


def get_users() -> List[Dict]:
    """
    Fetch all users from Overseerr.

    Returns:
        List of user dictionaries from Overseerr API.

    Raises:
        requests.exceptions.RequestException: If the API request fails.
    """
    headers = {"X-Api-Key": OVERSEERR_API_KEY}
    response = requests.get(f"{OVERSEERR_BASE_URL}/user", headers=headers, timeout=10)
    response.raise_for_status()

    data = response.json()
    return data.get("results", [])


def find_user(identifier: str) -> Optional[Dict]:
    """
    Find an Overseerr user by identifier.

    The identifier can be:
    - Plex username
    - Email address
    - Display name

    Search is case-insensitive.

    Args:
        identifier: The username, email, or display name to search for.

    Returns:
        User dictionary if found, None otherwise.
    """
    try:
        users = get_users()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch users from Overseerr: {e}")
        return None

    identifier_lower = identifier.lower()

    for user in users:
        # Check plexUsername
        if user.get("plexUsername", "").lower() == identifier_lower:
            return user

        # Check email
        if user.get("email", "").lower() == identifier_lower:
            return user

        # Check displayName
        if user.get("displayName", "").lower() == identifier_lower:
            return user

    return None


def get_user_notifications(user_id: int) -> Optional[Dict]:
    """
    Fetch notification settings for a specific Overseerr user.

    The bulk /user endpoint does not include notification settings, so we must
    fetch them separately per-user.

    Args:
        user_id: The Overseerr user ID.

    Returns:
        Notification settings dictionary if found, None otherwise.
    """
    headers = {"X-Api-Key": OVERSEERR_API_KEY}

    # Try the notifications endpoint first
    try:
        url = f"{OVERSEERR_BASE_URL}/user/{user_id}/settings/notifications"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to fetch notifications endpoint for user {user_id}: {e}")

    # Fallback: try getting full user data and extract notifications
    try:
        url = f"{OVERSEERR_BASE_URL}/user/{user_id}"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        user_data = response.json()
        settings = user_data.get("settings") or {}
        notifications = settings.get("notifications") or {}

        # Some Overseerr versions may have flattened notification keys at the top level
        # Merge both to handle different API versions
        merged = {}

        # Check for top-level notification keys
        for key in ["discordId", "discordEnabled", "discordEnabledTypes", "notificationTypes", "emailEnabled"]:
            if key in user_data and user_data[key] is not None:
                merged[key] = user_data[key]

        # Layer in nested notification settings (takes priority)
        for key, value in notifications.items():
            merged[key] = value

        return merged if merged else None

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch user data for user {user_id}: {e}")
        return None


def find_user_by_discord_id(discord_id: str) -> Optional[Dict]:
    """
    Find an Overseerr user by their linked Discord ID.

    Note: The bulk /user endpoint does NOT include notification settings,
    so we must fetch notification settings for each user individually.

    Args:
        discord_id: The Discord user ID (snowflake) to search for.

    Returns:
        User dictionary with _notificationSettings key if found, None otherwise.
    """
    try:
        users = get_users()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch users from Overseerr: {e}")
        return None

    for user in users:
        user_id = user.get("id")
        if user_id is None:
            continue

        # Fetch notification settings for this user
        notif = get_user_notifications(user_id)
        if not notif:
            continue

        # Compare as strings to handle type mismatches
        if str(notif.get("discordId")) == str(discord_id):
            # Return merged user data with notification settings
            merged = dict(user)
            merged["_notificationSettings"] = notif
            return merged

    return None


def update_user_notifications(user_id: int, discord_id: Optional[str], enable: bool) -> bool:
    """
    Update a user's Discord notification settings in Overseerr.

    Args:
        user_id: The Overseerr user ID.
        discord_id: The Discord user ID (snowflake), or None to unlink.
        enable: True to enable Discord notifications, False to disable.

    Returns:
        True if successful, False otherwise.

    Raises:
        requests.exceptions.RequestException: If the API request fails.
    """
    headers = {
        "X-Api-Key": OVERSEERR_API_KEY,
        "Content-Type": "application/json"
    }

    # discordEnabledTypes bitmask:
    # 0 = none, 4 = Request Approved, 8 = Request Available, 12 = both
    payload = {
        "notificationTypes": {
            "discord": 12 if enable else 0,  # Enable both Request Approved (4) and Request Available (8)
            "email": 0,
            "pushbullet": 0,
            "pushover": 0,
            "slack": 0,
            "telegram": 0,
            "webhook": 0,
            "webpush": 0
        },
        "emailEnabled": False,
        "pgpKey": None,
        "discordEnabled": enable,
        "discordEnabledTypes": 12 if enable else 0,
        "discordId": discord_id,
        "pushbulletAccessToken": None,
        "pushoverApplicationToken": None,
        "pushoverUserKey": None,
        "pushoverSound": None,
        "telegramEnabled": False,
        "telegramBotUsername": None,
        "telegramChatId": None,
        "telegramSendSilently": False
    }

    url = f"{OVERSEERR_BASE_URL}/user/{user_id}/settings/notifications"

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully updated notifications for user {user_id} (Discord ID: {discord_id}, enabled: {enable})")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to update notifications for user {user_id}: {e}")
        return False
