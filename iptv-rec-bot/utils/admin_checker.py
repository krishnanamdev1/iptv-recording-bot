import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import aiofiles

ADMIN_FILE = "temp_admins.json"

async def is_temp_admin(user_id: int) -> bool:
    """
    Check if a user is a temporary admin and their access is still valid.
    
    Args:
        user_id: The user ID to check.
        
    Returns:
        bool: True if the user is a temporary admin and their access is still valid.
    """
    if not os.path.exists(ADMIN_FILE):
        return False

    try:
        async with aiofiles.open(ADMIN_FILE, mode="r") as f:
            content = await f.read()
            admins: Dict[str, str] = json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return False

    expiry = admins.get(str(user_id))
    if not expiry:
        return False

    # Check if the expiry time is still valid
    expiry_time = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
    return datetime.now() < expiry_time

async def remove_temp_admin(user_id: int) -> bool:
    """
    Remove a user from the temporary admin list.
    
    Args:
        user_id: The user ID to remove.
        
    Returns:
        bool: True if the user was successfully removed, False otherwise.
    """
    if not os.path.exists(ADMIN_FILE):
        return False

    try:
        async with aiofiles.open(ADMIN_FILE, mode="r") as f:
            content = await f.read()
            admins: Dict[str, str] = json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return False

    if str(user_id) in admins:
        del admins[str(user_id)]
        async with aiofiles.open(ADMIN_FILE, mode="w") as f:
            await f.write(json.dumps(admins, indent=2))
        return True

    return False

async def add_temp_admin(user_id: int, expiry: str) -> bool:
    """
    Add a user to the temporary admin list with an expiry time.
    
    Args:
        user_id: The user ID to add.
        expiry: The expiry time in the format "%Y-%m-%d %H:%M:%S".
        
    Returns:
        bool: True if the user was successfully added, False otherwise.
    """
    try:
        # Load existing admins
        admins: Dict[str, str] = {}
        if os.path.exists(ADMIN_FILE):
            async with aiofiles.open(ADMIN_FILE, mode="r") as f:
                content = await f.read()
                admins = json.loads(content)

        # Add/update the user
        admins[str(user_id)] = expiry

        # Save the updated admins
        async with aiofiles.open(ADMIN_FILE, mode="w") as f:
            await f.write(json.dumps(admins, indent=2))
        return True
    except Exception as e:
        print(f"Error adding temporary admin: {e}")
        return False

async def cleanup_expired_admins() -> None:
    """
    Clean up expired temporary admins from the file.
    """
    if not os.path.exists(ADMIN_FILE):
        return

    try:
        async with aiofiles.open(ADMIN_FILE, mode="r") as f:
            content = await f.read()
            admins: Dict[str, str] = json.loads(content)

        # Filter out expired admins
        current_time = datetime.now()
        active_admins = {
            user_id: expiry
            for user_id, expiry in admins.items()
            if current_time < datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
        }

        # Save the updated list if changes were made
        if len(active_admins) != len(admins):
            async with aiofiles.open(ADMIN_FILE, mode="w") as f:
                await f.write(json.dumps(active_admins, indent=2))
    except Exception as e:
        print(f"Error cleaning up expired admins: {e}")

async def get_admin_expiry_time(user_id: int) -> Optional[datetime]:
    """
    Get the expiry time of a temporary admin.
    
    Args:
        user_id: The user ID to check.
        
    Returns:
        Optional[datetime]: The expiry time as a datetime object, or None if the user is not a temporary admin.
    """
    if not os.path.exists(ADMIN_FILE):
        return None

    try:
        async with aiofiles.open(ADMIN_FILE, mode="r") as f:
            content = await f.read()
            admins: Dict[str, str] = json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

    expiry = admins.get(str(user_id))
    if not expiry:
        return None

    return datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
