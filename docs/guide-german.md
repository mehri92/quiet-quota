# Quiet Quota · Windows-Beta 0.3.1

Ein dezenter Hinweis auf das gemeinsame Wochenkontingent von ChatGPT Work und
Codex. Die Prozentzahl bedeutet **verbraucht**, nicht verbleibend. Gewöhnliche
ChatGPT-Chats und weitere Funktionslimits werden damit nicht pauschal erfasst.

## Sprache und Update

Englisch ist jetzt Standard. Rechtsklick auf das Tray-Symbol → **Settings → Language → Deutsch → Save**. Weitere Sprachen: Spanisch, Französisch, Portugiesisch, Italienisch, Japanisch und vereinfachtes Chinesisch.

Die Auswahl wirkt sofort auf Einstellungen, Tray-Menü und sichtbare Popups. Speichern behält die Sprache dauerhaft; Abbrechen oder Schließen stellt die vorherige Sprache überall wieder her. Ein Sprachwechsel löst keine zusätzliche Meldung aus und verlängert deren Anzeigezeit nicht.

Zum Aktualisieren die laufende App im Tray beenden und die neuen Dateien in denselben Programmordner kopieren. `.venv` behalten. Deine Einstellungen und Warnhistorie bleiben erhalten. Alle ausgelieferten Dateinamen sind englisch. Vorhandene Desktop- und Autostartverknüpfungen neu auf `Start.cmd` anlegen. Alte deutsche Startdateien nach dem Update aus dem Programmordner entfernen.

Bildschirmecke, Monitor und Animation wirken ebenfalls sofort; Abbrechen stellt die vorherigen Werte wieder her. Warnschwellen, Anzeigedauer und Abfrageintervall werden erst mit Speichern übernommen.

## Start

1. ZIP vollständig in einen eigenen Ordner entpacken.
2. Python 3.10 oder neuer für Windows installieren, inklusive Python Launcher:
   https://www.python.org/downloads/windows/
3. `Setup.cmd` doppelklicken. Das legt eine lokale Python-Umgebung an und
   installiert PySide6 für Fenster, Animation und Tray-Symbol. Kein Administrator nötig.
4. `Demo.cmd` zeigt ein Beispiel mit 67 %. Rechtsklick auf das kleine Symbol neben
   der Uhr öffnet Einstellungen und weitere Tests. Das Symbol kann im ausgeklappten
   Infobereich unter dem Pfeil liegen. Demo danach über **Beenden** schließen.
5. `Start.cmd` startet die Live-Abfrage. Fehlen Codex oder die Anmeldung, öffnet
   sich das Verbindungsfenster. Es ist auch über **Verbindung** im Tray-Menü oder
   unten links in den Einstellungen erreichbar.
6. Fehlt die native Windows-Codex-CLI, öffne die Installationsanleitung im
   Verbindungsfenster. Installiere sie und klicke auf **Erneut prüfen**. Wird sie
   weiterhin nicht erkannt, starte Quiet Quota neu. Die Desktop-App allein oder
   eine Installation nur in WSL genügt möglicherweise nicht.
7. Klicke auf **Mit ChatGPT verbinden** und melde dich im Browser an. Codex
   übernimmt die Anmeldung und Speicherung der Zugangsdaten. Quiet Quota fragt
   weder nach deinem Passwort noch nach einem API-Key.
8. Warte auf **Verbunden · …% diese Woche verbraucht** und schließe das Fenster.
   Eine erfolgreiche Anmeldung ohne abrufbares Wochenlimit wird gesondert angezeigt.
   Der erste Abruf setzt still den Ausgangsstand; die nächste Schwelle löst den Hinweis aus.

Vorhandene Codex-Anmeldungen werden automatisch genutzt. **Erneut anmelden** kann
auch das Konto deiner lokalen Codex CLI ändern. Abbrechen beendet eine laufende
Anmeldung, meldet ein bestehendes Konto aber nicht ab. Eine Anmeldung läuft nach
fünf Minuten ab und kann wiederholt werden. Erfolgreiches Verbinden aus der Demo
wechselt direkt zur Live-Abfrage.

Wenn kein Symbol erscheint: `Diagnostics.cmd` starten und die sichtbare Fehlermeldung
prüfen. Bei Abfrageproblemen steht die Ursache im Tray-Menü. Fehlende Installation oder Anmeldung öffnet die Verbindungshilfe einmal pro Start;
sonstige Abfragefehler erzeugen keine wiederholten Popups. Zum Beenden das Tray-Menü verwenden.

## Verhalten

- Standardschwellen: 50, 75, 90, 95 Prozent Verbrauch; in den Einstellungen änderbar.
- Ampel: Grün über 50 % verbleibend, Gelb ab 50 % verbleibend, Rot ab 20 % verbleibend (50 % bzw. 80 % Verbrauch). Farben sind unabhängig von
  individuell geänderten Meldeschwellen.
- Mindestens 264 × 76 logische Pixel, Breite je nach Sprache und Schrift; 28 Pixel sanftes Hinein-/Herausgleiten; vier Sekunden sichtbar.
- Kein Ton, kein Tastaturfokus, keine Mausklicks abfangen. DPI-Skalierung durch Qt.
- Monitor und jede der vier Ecken auswählbar; Taskleistenfläche wird ausgespart.
- Hintergrundabfrage alle zwei Minuten. Das ist **keine** Popup-Frequenz.
- Pro Reset-Zeitraum jede Schwelle einmal. Neustarts lösen sie nicht erneut aus.
- Bei übersprungenen Schwellen nur eine Meldung mit dem aktuellen Verbrauch.
- Erste Einrichtung mitten in der Woche: keine rückwirkenden Warnungen.
- Windows-Vollbild-/Präsentations-/Ruhezustände werden über
  `SHQueryUserNotificationState` berücksichtigt. Aufgeschobene Schwellen werden bei
  einem späteren erfolgreichen Abruf zusammengefasst angezeigt. Die Erkennung
  hängt davon ab, ob Windows die jeweilige Anwendung entsprechend meldet.
- Manuelle Pause über das Tray-Menü. Test-Popups und manuell angezeigter Stand
  umgehen die Pause absichtlich.
- Kein automatischer Windows-Autostart. Wenn gewünscht, eine Verknüpfung zu
  `Start.cmd` im persönlichen Autostartordner ablegen.
- Nur eine Instanz gleichzeitig; Demo und Live-Modus sind alternative Starts.

## Datenquelle und Privatsphäre

Das Tool startet einen eigenen `codex app-server` über lokale Standard-Ein-/Ausgabe.
Es liest `account/read` und `account/rateLimits/read` nach dem
Protokoll-Handshake. Bei ausdrücklich gestarteter Anmeldung verwendet es außerdem
`account/login/start` und bei Abbruch `account/login/cancel`. Es startet keine Chats, Prompts oder Modell-Inferenz und
benötigt weder eine lokale KI noch GPU-Rechenleistung. Codex übernimmt Anmeldung
und die Verbindung zum Dienst. Das Tool liest keine Browser-Cookies oder Token-Dateien.

Es akzeptiert nur den allgemeinen `codex`-Bucket mit explizit 10.080 Minuten
Fensterdauer. Fehlt das Wochenlimit, wird kein Prozentwert erfunden. Weitere
modellabhängige Buckets werden nicht addiert. Neue Dienst- oder Protokollversionen
können Anpassungen nötig machen.

Einstellungen und bereits gemeldete Schwellen liegen unter
`%LOCALAPPDATA%\QuietQuota`. Ein Hash der Kontometadaten trennt Zustände; rohe
Kontometadaten werden dort nicht gespeichert. Anmeldeinformationen verwaltet
weiterhin Codex. Beim Beenden wird nur der von diesem Tool gestartete
app-server-Prozessbaum beendet, keine anderen Codex-Sitzungen.

## Entwicklungs- und Teststand

Quellcode enthalten. Tests: `python -m unittest discover -v`.
Die Schwellenlogik, Reset-/Neustart-/Pause-Fälle, Datenvalidierung und der
read-only JSONL-Handshake werden automatisiert geprüft. Die Qt-Oberfläche wird
offscreen geprüft. Kein Live-Test mit deinem Konto oder einem echten
Windows-Desktop in dieser Umgebung: Fokus, Tray, Vollbildverhalten und lokale
Codex-Anbindung bitte zuerst mit der Demo bzw. deinem ersten Live-Abruf prüfen.
Es handelt sich um ein Python-Tool, nicht um eine signierte EXE.

Offizielle Grundlagen (abgerufen am 19.10.2026):
- Gemeinsame Work-/Codex-Limits: https://learn.chatgpt.com/docs/pricing
- RPC und Rate-Limit-Felder: https://learn.chatgpt.com/docs/app-server
- Qt-Fensterflags: https://doc.qt.io/qt-6/qt.html#WindowType-enum

## Unterstützung

Der kleine Ko-fi-Link unten in den Einstellungen öffnet die Unterstützungsseite nur beim Anklicken. Offene Änderungen bleiben erhalten. Das neue Q-Symbol erscheint im Fenstertitel und Tray; für Windows-Verknüpfungen liegt es unter `assets/quiet-quota.ico`.
