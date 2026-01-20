"""
VDF Wrapper - Uses standalone parser
Speichern als: src/utils/vdf_wrapper.py
"""

from pathlib import Path
from typing import Dict
from src.utils.appinfo_vdf_parser import AppInfoParser

class AppInfoVDF:
    """Wrapper für appinfo.vdf Parsing"""
    
    @staticmethod
    def load(file_path: Path) -> Dict:
        return AppInfoParser.load(file_path)
    
    @staticmethod
    def dump(data: Dict, file_path: Path) -> bool:
        return AppInfoParser.dump(data, file_path)
