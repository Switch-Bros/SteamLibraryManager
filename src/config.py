"""Configuration"""
import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    APP_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = APP_DIR / 'data'
    CACHE_DIR: Path = DATA_DIR / 'cache'
    
    STEAM_API_KEY: str = os.getenv('STEAM_API_KEY', '')
    STEAM_PATH: Path = None
    STEAM_USER_ID: str = None
    
    DEFAULT_LOCALE: str = 'en'
    THEME: str = 'dark'
    WINDOW_WIDTH: int = 1400
    WINDOW_HEIGHT: int = 800
    
    def __post_init__(self):
        self.DATA_DIR.mkdir(exist_ok=True)
        self.CACHE_DIR.mkdir(exist_ok=True)
        if self.STEAM_PATH is None:
            self.STEAM_PATH = self._find_steam_path()
    
    def _find_steam_path(self):
        paths = [
            Path.home() / '.steam' / 'steam',
            Path.home() / '.local' / 'share' / 'Steam',
        ]
        for p in paths:
            if p.exists():
                return p
        return None
    
    def get_all_user_ids(self):
        if not self.STEAM_PATH:
            return []
        userdata = self.STEAM_PATH / 'userdata'
        if not userdata.exists():
            return []
        ids = []
        for item in userdata.iterdir():
            if item.is_dir() and item.name.isdigit():
                if (item / 'config' / 'localconfig.vdf').exists():
                    ids.append(item.name)
        return ids

config = Config()
