"""
Skript zum Übertragen von Steam-Kategorien (Tags) aus sharedconfig.vdf nach localconfig.vdf
"""
import sys
from pathlib import Path

# Füge das src Verzeichnis zum Python-Pfad hinzu
sys.path.append(str(Path(__file__).parent))

from src.core.localconfig_parser import LocalConfigParser


def find_apps_section(data):
    """Durchsucht die VDF-Struktur dynamisch nach der 'apps' Sektion"""
    # Mögliche Root-Keys in Steam Configs
    roots = ['UserLocalConfigStore', 'UserRoamingConfigStore']

    for root in roots:
        if root in data:
            try:
                # Der Standard-Pfad zu den Apps
                return data[root]['Software']['Valve']['Steam']['apps']
            except KeyError:
                continue
    return None


def merge_tags():
    # Dateien definieren
    source_file = Path("sharedconfig.vdf")  # Die Windows Datei mit den Tags
    target_file = Path("localconfig_lin.vdf")  # Deine Linux Datei

    if not source_file.exists():
        print(f"❌ Quelldatei fehlt: {source_file}")
        return
    if not target_file.exists():
        print(f"❌ Zielldatei fehlt: {target_file}")
        return

    print(f"📂 Lade Quelle (Tags): {source_file}...")
    parser_source = LocalConfigParser(source_file)
    if not parser_source.load():
        print("❌ Fehler beim Laden der Quelle.")
        return

    print(f"📂 Lade Ziel (Linux): {target_file}...")
    parser_target = LocalConfigParser(target_file)
    if not parser_target.load():
        print("❌ Fehler beim Laden des Ziels.")
        return

    # Finde die Apps in der Quelle (da parser_source.apps evtl. leer ist, wenn Pfad anders)
    source_apps = find_apps_section(parser_source.data)

    # Fallback: Wenn find_apps_section nichts findet, versuche parser.apps (falls es doch passt)
    if not source_apps:
        source_apps = parser_source.apps

    if not source_apps:
        print("❌ Konnte 'apps' Sektion in der Quelldatei nicht finden!")
        print("   Struktur ist anders als erwartet.")
        return

    print(f"ℹ️ Quelle enthält {len(source_apps)} Spiele-Einträge.")

    count_merged = 0

    # Iteriere durch alle Spiele in der Quelle (sharedconfig)
    for app_id, app_data in source_apps.items():
        # Suche nach Tags (Steam nutzt mal 'tags', mal 'Tags')
        tags = app_data.get('tags') or app_data.get('Tags')

        if tags:
            # Wir haben Tags gefunden!

            # Konvertiere Dict {"0": "RPG"} zu Liste ["RPG"] falls nötig
            if isinstance(tags, dict):
                tag_list = list(tags.values())
            elif isinstance(tags, list):
                tag_list = tags
            else:
                continue

            # Hole aktuelle Tags aus Ziel-Datei zum Vergleich
            # KORREKTUR: get_app_categories statt get_app_tags
            current_tags = parser_target.get_app_categories(app_id)

            # Wenn unterschiedlich, schreibe in Ziel-Datei
            if sorted(tag_list) != sorted(current_tags):
                # KORREKTUR: set_app_categories statt set_app_tags
                parser_target.set_app_categories(app_id, tag_list)
                count_merged += 1

    if count_merged > 0:
        print(f"✅ {count_merged} Spiele erfolgreich mit Kategorien aktualisiert!")

        if parser_target.save():
            print(f"💾 Datei gespeichert: {target_file}")
            print("\n🚀 NÄCHSTE SCHRITTE:")
            print("1. Beende Steam komplett.")
            print(f"2. Kopiere '{target_file}' nach:")
            print("   /home/heikesfootslave/.local/share/Steam/userdata/[DEINE_ID]/config/localconfig.vdf")
            print("   (Überschreibe die dortige Datei bzw. benenne sie vorher um)")
            print("3. Starte Steam neu.")
        else:
            print("❌ Fehler beim Speichern der Zieldatei.")
    else:
        print("⚠️ Keine neuen Tags zum Übertragen gefunden.")
        print("   Entweder sind die Dateien identisch oder die App-IDs stimmen nicht überein.")


if __name__ == "__main__":
    merge_tags()