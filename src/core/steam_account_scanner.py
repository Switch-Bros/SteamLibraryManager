"""
Steam Account Scanner.

This module scans the Steam userdata directory to find all local Steam accounts
and fetches their display names from the Steam Community XML API.
"""
from pathlib import Path
from typing import List, Optional
import requests
import xml.etree.ElementTree as ET

from src.core.steam_account import SteamAccount
from src.utils.i18n import t


# Steam ID conversion constant
# This is the base value that converts Account ID (32-bit) to SteamID64
# Source: https://developer.valvesoftware.com/wiki/SteamID
STEAM_ID_BASE = 76561197960265728  # 0x0110000100000000


def account_id_to_steam_id_64(account_id: int) -> int:
    """Convert Account ID (32-bit) to SteamID64.
    
    Args:
        account_id: The short Steam account ID (from userdata folder)
        
    Returns:
        The 64-bit Steam ID
        
    Example:
        >>> account_id_to_steam_id_64(4190954)
        76561198004190954
    """
    return account_id + STEAM_ID_BASE


def steam_id_64_to_account_id(steam_id_64: int) -> int:
    """Convert SteamID64 back to Account ID (32-bit).
    
    Args:
        steam_id_64: The 64-bit Steam ID
        
    Returns:
        The short Steam account ID
        
    Example:
        >>> steam_id_64_to_account_id(76561198004190954)
        4190954
    """
    return steam_id_64 - STEAM_ID_BASE


def fetch_steam_display_name(steam_id_64: int) -> str:
    """Fetch the Steam profile display name from Steam Community XML API.
    
    Uses the same API as Depressurizer and our existing code.
    
    Args:
        steam_id_64: The 64-bit Steam ID
        
    Returns:
        The user's Steam profile display name, or the SteamID64 as fallback
    """
    try:
        url = f"https://steamcommunity.com/profiles/{steam_id_64}?xml=1"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            tree = ET.fromstring(response.content)
            steam_id_element = tree.find('steamID')
            
            if steam_id_element is not None and steam_id_element.text:
                return steam_id_element.text
                
    except (requests.RequestException, ET.ParseError) as e:
        print(f"Warning: Could not fetch display name for {steam_id_64}: {e}")
    except Exception as e:
        print(f"Unexpected error fetching Steam display name: {e}")
    
    # Fallback to SteamID64
    return str(steam_id_64)


def scan_steam_accounts(steam_path: str) -> List[SteamAccount]:
    """Scan the Steam userdata directory for all local accounts.
    
    This function:
    1. Scans the userdata/ folder for account directories
    2. Converts account IDs to SteamID64
    3. Fetches display names from Steam Community API
    
    Args:
        steam_path: Path to the Steam installation directory
        
    Returns:
        List of SteamAccount objects, sorted by display name
        
    Example:
        >>> accounts = scan_steam_accounts("/home/user/.steam")
        >>> for acc in accounts:
        ...     print(f"{acc.account_id}: {acc.display_name}")
        4190954: HeikesFootSlave
        87654321: OtherUser
    """
    userdata_path = Path(steam_path) / "userdata"
    accounts = []
    
    if not userdata_path.exists():
        print(f"Warning: userdata directory not found: {userdata_path}")
        return accounts
    
    print(f"Scanning Steam accounts in: {userdata_path}")
    
    for account_dir in userdata_path.iterdir():
        # Only process directories with numeric names (account IDs)
        if account_dir.is_dir() and account_dir.name.isdigit():
            try:
                account_id = int(account_dir.name)
                steam_id_64 = account_id_to_steam_id_64(account_id)
                
                print(f"Found account: {account_id} → SteamID64: {steam_id_64}")
                
                # Fetch display name (may take a moment)
                display_name = fetch_steam_display_name(steam_id_64)
                
                accounts.append(SteamAccount(
                    account_id=account_id,
                    steam_id_64=steam_id_64,
                    display_name=display_name
                ))
                
                print(f"  → Display name: {display_name}")
                
            except ValueError as e:
                print(f"Warning: Invalid account directory name: {account_dir.name}")
            except Exception as e:
                print(f"Error processing account {account_dir.name}: {e}")
    
    # Sort by display name for better UX
    accounts.sort(key=lambda a: a.display_name.lower())
    
    print(f"Total accounts found: {len(accounts)}")
    return accounts


def is_steam_running() -> bool:
    """Check if Steam is currently running.
    
    This checks for the Steam process on the system.
    On Linux: looks for 'steam' process
    On Windows: looks for 'steam.exe' process
    
    Returns:
        True if Steam is running, False otherwise
    """
    try:
        import psutil
        
        for proc in psutil.process_iter(['name']):
            proc_name = proc.info.get('name', '').lower()
            if 'steam' in proc_name:
                # Ignore helper processes like steamwebhelper
                if proc_name in ['steam', 'steam.exe']:
                    return True
        
        return False
        
    except ImportError:
        print("Warning: psutil not installed, cannot check if Steam is running")
        return False
    except Exception as e:
        print(f"Error checking if Steam is running: {e}")
        return False


def kill_steam_process() -> bool:
    """Kill the Steam process.
    
    WARNING: This forcefully terminates Steam. Use with caution!
    Only call this after user confirmation.
    
    Returns:
        True if Steam was successfully killed, False otherwise
    """
    try:
        import psutil
        import time
        
        killed = False
        
        for proc in psutil.process_iter(['name', 'pid']):
            proc_name = proc.info.get('name', '').lower()
            
            # Only kill main Steam process, not helpers
            if proc_name in ['steam', 'steam.exe']:
                print(f"Killing Steam process (PID: {proc.info['pid']})")
                proc.kill()
                killed = True
        
        if killed:
            # Wait a moment for process to fully terminate
            time.sleep(1)
            
            # Verify it's actually closed
            if not is_steam_running():
                print("✅ Steam successfully closed")
                return True
            else:
                print("⚠️ Steam process still running after kill attempt")
                return False
        else:
            print("No Steam process found to kill")
            return False
        
    except ImportError:
        print("Error: psutil not installed, cannot kill Steam process")
        return False
    except Exception as e:
        print(f"Error killing Steam process: {e}")
        return False
