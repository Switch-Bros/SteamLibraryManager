"""i18n System"""
import json
from pathlib import Path
from typing import Optional, Dict, Any

class I18n:
    def __init__(self, locale: str = 'en'):
        self.locale = locale
        self.translations: Dict[str, Any] = {}
        self.fallback_translations: Dict[str, Any] = {}
        self.locales_dir = Path(__file__).parent.parent.parent / 'locales'
        self._load_translations()
    
    def _load_translations(self):
        fallback_path = self.locales_dir / 'en.json'
        if fallback_path.exists():
            with open(fallback_path, 'r', encoding='utf-8') as f:
                self.fallback_translations = json.load(f)
        
        if self.locale != 'en':
            locale_path = self.locales_dir / f'{self.locale}.json'
            if locale_path.exists():
                with open(locale_path, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
            else:
                self.translations = self.fallback_translations.copy()
        else:
            self.translations = self.fallback_translations.copy()
    
    def t(self, key: str, **kwargs) -> str:
        keys = key.split('.')
        value = self.translations
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break
        
        if value is None:
            value = self.fallback_translations
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    value = None
                    break
        
        if value is None:
            return f"[{key}]"
        
        if not isinstance(value, str):
            return f"[{key}: not a string]"
        
        if kwargs:
            try:
                return value.format(**kwargs)
            except:
                return value
        
        return value

_i18n_instance: Optional[I18n] = None

def init_i18n(locale: str = 'en') -> I18n:
    global _i18n_instance
    _i18n_instance = I18n(locale)
    return _i18n_instance

def t(key: str, **kwargs) -> str:
    if _i18n_instance is None:
        init_i18n()
    return _i18n_instance.t(key, **kwargs)

def get_i18n() -> I18n:
    if _i18n_instance is None:
        init_i18n()
    return _i18n_instance
