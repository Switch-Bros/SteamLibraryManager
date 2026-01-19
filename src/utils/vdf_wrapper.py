"""
VDF Wrapper - Uses standalone parser

Speichern als: src/utils/vdf_wrapper.py
"""

from pathlib import Path
from typing import Dict


class AppInfoVDF:
    """Wrapper für appinfo.vdf Parsing"""
    
    @staticmethod
    def load(file_path: Path) -> Dict:
        from src.utils.appinfo_vdf_parser import AppInfoParser
        return AppInfoParser.load(file_path)
    
    @staticmethod
    def dump(data: Dict, file_path: Path) -> bool:
        from src.utils.appinfo_vdf_parser import AppInfoParser
        return AppInfoParser.dump(data, file_path)


def load_appinfo(file_path: Path) -> Dict:
    return AppInfoVDF.load(file_path)

def save_appinfo(data: Dict, file_path: Path) -> bool:
    return AppInfoVDF.dump(data, file_path)
