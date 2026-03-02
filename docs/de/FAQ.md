# ❓ Häufig gestellte Fragen

---

## Allgemein

### Was ist SLM?

Steam Library Manager (SLM) ist ein Linux-natives Werkzeug zur Organisation großer Steam-Spielebibliotheken. Es erstellt, bearbeitet und verwaltet Steam-Sammlungen und -Kategorien — wie Depressurizer, aber für Linux gebaut und mit modernen Features.

### Ist SLM ein Ersatz für Depressurizer?

Ja. SLM hat volle Depressurizer-Feature-Parität (alle 17 AutoCat-Typen, Profile, Filter) plus Features, die Depressurizer nicht hat: Smart Collections mit ODER-Logik, ProtonDB-Integration, HLTB-Daten, Steam-Deck-Status, externe Spiele von 8 Plattformen und eine schnelle SQLite-Datenbank.

### Funktioniert SLM unter Windows?

SLM ist Linux-first. Die Codebasis ist Python/PyQt6 und könnte theoretisch unter Windows laufen, ist aber für Linux konzipiert und getestet. Windows-Support könnte in Zukunft kommen.

### Ist SLM kostenlos?

Ja, SLM ist kostenlos und Open Source. Wenn du es nützlich findest, kannst du die Entwicklung über Hilfe → Unterstützen (PayPal, GitHub Sponsors oder Ko-fi) unterstützen.

### Verändert SLM meine Steam-Dateien?

SLM schreibt in Steams `cloud-storage-namespace-1.json` (die Cloud-Sammlungsdatei) und optional in `shortcuts.vdf` (für externe Spiele). Es erstellt vor jedem Schreibvorgang Backups. Deine Spielinstallationen werden nie angerührt.

---

## Setup & Installation

### Was sind die Systemvoraussetzungen?

- Linux (jede moderne Distribution)
- Python 3.11+ (wenn aus Quellcode)
- Steam installiert und mindestens einmal eingeloggt
- ~50 MB Speicherplatz für Anwendung + Datenbank

### Welche Steam-Accounts unterstützt SLM?

SLM funktioniert mit jedem Steam-Account, der auf deinem Rechner eingeloggt war. Beim ersten Start wählst du, welchen Account du verwalten willst. Du kannst den Account in den Einstellungen wechseln.

### Kann ich SLM benutzen, während Steam läuft?

Ja, aber mit Vorsicht. Wenn du Sammlungen gleichzeitig in SLM und Steam änderst, kann ein Konflikt auftreten. SLM behandelt das ordentlich (Backup + Warnung), aber am besten speicherst und schließt du SLM, bevor du Änderungen in Steam machst.

### Mein Steam ist an einem nicht-standardmäßigen Ort installiert

Gehe zu Einstellungen (`Strg+P`) → Allgemein → Steam-Pfad und setze den korrekten Pfad. SLM erkennt `~/.steam` und `~/.local/share/Steam` automatisch, unterstützt aber jeden Ort.

---

## Sicherheit & Datenschutz

### Ist es sicher, sich über SLM bei Steam einzuloggen?

Ja. SLM nutzt Steams offizielle OAuth2-API (`IAuthenticationService`) — dasselbe Authentifizierungssystem, das auch der Steam Desktop Client verwendet. Beim QR-Code-Login (empfohlen) sieht SLM dein Passwort nicht einmal. Beim Passwort-Login wird dein Passwort mit Steams RSA Public Key verschlüsselt, bevor es dein System verlässt.

### Kann SLM mein Inventar stehlen oder meine Items handeln?

Nein. Das ist technisch unmöglich. SLM hat keine Trade-Endpunkte implementiert, und die OAuth-Token-Scopes erlauben weder Trades noch Käufe. Steam verlangt für alle Trades zusätzlich eine Mobile-Bestätigung, die SLM nicht auslösen kann.

### Was kann SLM tatsächlich mit meinem Account machen?

SLMs Zugriff ist beschränkt auf: Spieleliste lesen, Sammlungen lesen und schreiben, und Steam-Store-Metadaten abrufen. Es kann weder dein Passwort ändern, noch deine E-Mail ändern, Steam Guard deaktivieren, Käufe tätigen oder auf dein Inventar zugreifen.

### Wie werden meine Login-Tokens gespeichert?

Tokens werden über deinen System-Keyring gespeichert (KWallet bei KDE, GNOME Keyring, etc.) — derselbe sichere Speicher, den auch dein Browser für Passwörter nutzt. Falls kein Keyring verfügbar ist, nutzt SLM AES-GCM-verschlüsselte Dateien, deren Schlüssel über PBKDF2 aus deiner Machine-ID abgeleitet wird. Tokens werden niemals im Klartext gespeichert.

### Brauche ich einen Steam-API-Key?

Nein. Der Steam-API-Key ist optional. SLMs primäre Methode liest deine Spiele direkt aus lokalen Steam-Dateien (licensecache, packageinfo.vdf). Der API-Key ermöglicht nur einige zusätzliche Metadaten-Abfragen und wird lokal in deiner Konfiguration gespeichert — nie an Dritte übertragen.

### Sammelt SLM irgendwelche Daten oder telefoniert nach Hause?

Nein. SLM hat keinerlei Telemetrie und macht keine Netzwerkaufrufe außer an Steams API, SteamGridDB, HowLongToBeat und ProtonDB. Du kannst das selbst überprüfen:
```bash
grep -r "requests\.\(get\|post\)" src/ | grep -v test | grep -v __pycache__
```

### Wie widerrufe ich SLMs Zugriff auf meinen Account?

Drei Möglichkeiten: Einstellungen → Logout in SLM (löscht alle lokalen Tokens), https://store.steampowered.com/twofactor/manage besuchen um alle Geräte zu deautorisieren, oder einfach `~/.config/SteamLibraryManager/tokens.enc` löschen.

### Ich habe ein teures Inventar. Sollte ich mir Sorgen machen?

Nein. Selbst im schlimmsten Fall, wenn jemand deinen Token stehlen würde, könnte er nur deine Spieleliste lesen — keine Items handeln, keine Käufe tätigen und keine Account-Einstellungen ändern. Mit aktivem 2FA bleibt dein Account in jedem Fall sicher.

---

## Sammlungen & Kategorien

### Was ist der Unterschied zwischen einer Sammlung und einer Smart Collection?

Eine **Sammlung** ist ein manueller Ordner — du fügst Spiele selbst hinzu und entfernst sie. Eine **Smart Collection** ist regelbasiert — sie schließt automatisch jedes Spiel ein, das deinen Kriterien entspricht, und aktualisiert sich selbst, wenn sich deine Bibliothek ändert.

### Synchronisieren meine Sammlungen zurück zu Steam?

Ja. SLM liest aus und schreibt in Steams Cloud Storage. Nach dem Speichern in SLM und einem Steam-Neustart erscheinen deine Sammlungen in Steams Bibliothek.

### Ich habe ein Chaos bei meinen Kategorien angerichtet. Kann ich das rückgängig machen?

Verwende Datei → Profile → Verwalten um ein gespeichertes Profil zu laden, oder Datei → Import → DB Backup um von einem Backup wiederherzustellen. Wenn du vor den Änderungen ein Profil gespeichert hast, kannst du deine vorherige Organisation vollständig wiederherstellen.

### Kann ein Spiel in mehreren Sammlungen sein?

Ja. Spiele können gleichzeitig beliebig vielen Sammlungen angehören, genau wie in Steam.

### Was bedeutet „Unkategorisiert"?

Spiele, die in keiner Sammlung sind. Das ist eine virtuelle Kategorie — du kannst keine Spiele hinzufügen, aber Spiele daraus in Sammlungen ziehen.

---

## Smart Collections

### Welche Operatoren kann ich verwenden?

UND (alle Bedingungen wahr), ODER (mindestens eine wahr), NICHT (entsprechende Spiele ausschließen). Du kannst diese verschachteln für komplexe Logik wie `(Genre = RPG ODER Genre = Strategie) UND Plattform = Linux UND NICHT Status = Aufgegeben`.

### Warum zeigt meine Smart Collection 0 Spiele?

Höchstwahrscheinlich wurden die Metadaten, auf die deine Regeln basieren, noch nicht geladen. Führe zuerst das entsprechende Enrichment aus (Werkzeuge → Batch). Zum Beispiel brauchen HLTB-basierte Regeln HLTB-Enrichment, Deck-Regeln brauchen Deck-Status-Enrichment.

### Zählen Smart Collections gegen Steams Sammlungslimit?

Nein. Smart Collections werden lokal von SLM ausgewertet. Nur wenn du sie explizit „exportierst" oder zu regulären Sammlungen „konvertierst", werden sie zu Steam-Sammlungen.

---

## Auto-Kategorisierung

### Überschreibt AutoCat meine bestehenden Kategorien?

Nein. AutoCat fügt Spiele zu neuen Kategorien hinzu (z.B. „Genre: RPG"), entfernt sie aber nicht aus bestehenden. Deine manuelle Organisation bleibt erhalten.

### Was ist das beste AutoCat-Setup für eine große Bibliothek?

Für eine Bibliothek mit 1000+ Spielen empfehlen wir:
1. Zuerst Enrichment ausführen (Werkzeuge → Batch → ALLE Daten NEU einlesen)
2. Dann AutoCat mit: Genre + Tags (Top 3) + Plattform + Deck-Status
3. Optional: HLTB + Jahr für weitere Organisation

### Kann ich die Kategorienamen anpassen, die AutoCat erstellt?

AutoCat verwendet Präfix-Muster (z.B. „Genre: Action", „HLTB: Kurz"). Das Präfix-Format wird vom AutoCat-Typ bestimmt und folgt Steam-Community-Konventionen.

---

## Daten-Enrichment

### Woher kommen die Enrichment-Daten?

| Quelle | Anbieter | Rate Limits |
|--------|----------|-------------|
| Spielmetadaten | Steam Web API | ~200 Anfragen/5 Min. |
| HLTB-Zeiten | HowLongToBeat.com | ~1 Anfrage/Sek. |
| ProtonDB-Bewertungen | ProtonDB.com | Batch-API, schnell |
| Deck-Status | Steam-API | ~200 Anfragen/5 Min. |
| Erfolge | Steam Web API | ~200 Anfragen/5 Min. |

### Wie oft sollte ich Enrichment ausführen?

Einmal nach dem initialen Setup, dann gelegentlich wenn viele neue Spiele hinzukommen (z.B. nach einem Steam Sale). Einzelne Spieldaten können per Rechtsklick aktualisiert werden.

### Verwendet Enrichment meinen Steam-API-Key?

Nein. SLM nutzt Steams öffentliche API-Endpunkte, die keinen API-Key benötigen. Deine Steam-Login-Session wird nur für die Cloud-Storage-Synchronisation verwendet.

### HLTB-Daten scheinen für einige Spiele falsch

HLTB-Matching verwendet Fuzzy-Namensabgleich mit einer Genauigkeitsrate von 94,8%. Einige Spiele mit sehr generischen Namen oder großen Unterschieden zwischen Steam- und HLTB-Benennung können falsch zugeordnet werden. Das ist selten, aber zu erwarten.

---

## Externe Spiele

### Welche Plattformen werden unterstützt?

Epic Games Store, GOG Galaxy, Heroic Launcher, Lutris, Flatpak-Spiele, Bottles, itch.io und Amazon Games.

### Brauche ich die Plattform-Launcher installiert?

Ja. SLM liest die lokalen Konfigurationsdateien jeder Plattform, die nur existieren, wenn der Launcher installiert und mindestens einmal gestartet wurde.

### Kann ich Spiele aus Steam entfernen, die ich über Externe Spiele hinzugefügt habe?

Ja. Verwende den Externe-Spiele-Manager (`Strg+Umschalt+E`) um deine Nicht-Steam-Verknüpfungen zu verwalten. Dort entfernen löscht die Steam-Verknüpfung.

### Artwork wird für externe Spiele nicht heruntergeladen

SLM verwendet SteamGridDB für Artwork. Einige sehr nischige oder neue Spiele haben dort möglicherweise kein Artwork. Du kannst manuell Artwork über den Bildbrowser (`Strg+I`) hinzufügen.

---

## Performance

### Wie schnell ist SLM?

- Kaltstart (erster Start): 10-30 Sekunden (Datenbankaufbau)
- Warmstart (Folgestarts): < 3 Sekunden
- Kategorieneuaufbau: < 1 Sekunde für 3000 Spiele
- Suche: Sofort (< 100ms)

### Meine Bibliothek hat 5000+ Spiele. Schafft SLM das?

Ja. SLM ist für große Bibliotheken ausgelegt. Die SQLite-Datenbank und Batch-Operationen sind für 3000-5000+ Spiele optimiert. Einige Operationen (volles Enrichment) dauern länger, aber die UI bleibt responsiv.

### SLM verbraucht viel Arbeitsspeicher

Die lokale SQLite-Datenbank cached alle Metadaten für schnellen Zugriff. Für eine Bibliothek mit 3000 Spielen erwarte ~25-50 MB Datenbankgröße und ~100-200 MB RAM-Verbrauch. Das ist normal.

---

## Backup & Datensicherheit

### Wo speichert SLM seine Daten?

- Datenbank: `~/.local/share/SteamLibraryManager/steamlibmgr.db`
- Konfiguration: `~/.config/SteamLibraryManager/`
- Backups: `~/.local/share/SteamLibraryManager/backups/`

### Was passiert, wenn SLM beim Speichern abstürzt?

SLM erstellt vor jedem Schreibvorgang ein Backup der Cloud-Storage-Datei. Bei einem Absturz bleibt die Backup-Datei intakt. Beim nächsten Start verwendet SLM die neueste gültige Datei.

### Kann ich SLM-Daten zwischen mehreren Linux-Rechnern synchronisieren?

SLMs Sammlungen synchronisieren über Steams Cloud Storage, sie erscheinen also auf jedem Rechner, auf dem du dich bei Steam einloggst. Die lokale Datenbank (HLTB, ProtonDB, etc.) ist pro Rechner, kann aber schnell über Enrichment neu aufgebaut werden.

---

## Problemlösung

### „Zugriff verweigert"-Fehler

Stelle sicher, dass SLM Lese-/Schreibzugriff auf dein Steam-Verzeichnis hat. Bei Flatpak stelle sicher, dass das Steam-Verzeichnis in den Flatpak-Berechtigungen enthalten ist.

### Sammlungen verschwunden nach Steam-Update

Steam setzt gelegentlich den Cloud Storage zurück. Verwende Datei → Import → DB Backup um von deinem letzten Backup wiederherzustellen, oder Datei → Profile um ein gespeichertes Profil zu laden.

### Die App startet nicht

Prüfe die Logdatei unter `~/.local/share/SteamLibraryManager/steamlibmgr.log` für Fehlerdetails. Häufige Ursachen: fehlende Python-Abhängigkeiten, inkompatible PyQt6-Version oder Steam nicht installiert.

### Ich habe einen Bug gefunden!

Bitte melde ihn unter Hilfe → Online → Issues melden (oder direkt auf GitHub). Füge bei:
1. Was du gemacht hast
2. Was du erwartet hast
3. Was stattdessen passiert ist
4. Deine Logdatei (`~/.local/share/SteamLibraryManager/steamlibmgr.log`)

---

*Zuletzt aktualisiert: Februar 2026*
*Weitere Fragen? Besuche Hilfe → Online → Discussions*
