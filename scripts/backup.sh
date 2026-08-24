#!/usr/bin/env bash
# Sichert die Postgres-Datenbank in eine Datei mit Zeitstempel und entfernt
# Backups, die aelter als 7 Tage sind - im SmartDesk-Ordner auf dem Server
# ausfuehren (./scripts/backup.sh), idealerweise per Cron regelmaessig
# automatisch (siehe Kommentar ganz unten).
#
# "Wie lange werden alte Backups aufgehoben, bevor sie geloescht werden" nennt
# man eine Retention Policy - hier bewusst simpel (7 Tage, feste Zahl), damit
# die Festplatte des Servers nicht irgendwann von immer mehr Backups vollLAEUFT.
set -euo pipefail

# "$(dirname "$0")" ist der Ordner, in dem DIESES Skript selbst liegt (egal
# von wo aus man es aufruft) - "/.." geht eine Ebene hoch zum Projekt-Root.
# So funktioniert der Pfad unabhaengig davon, aus welchem Verzeichnis heraus
# man das Skript startet.
BACKUP_DIR="$(dirname "$0")/../backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/smartdesk-$TIMESTAMP.sql"

echo "==> Sichere Datenbank nach $BACKUP_FILE"
docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U smartdesk smartdesk > "$BACKUP_FILE"

echo "==> Entferne Backups aelter als 7 Tage"
# find ... -mtime +7: findet Dateien, deren letzte Aenderung laenger als 7
# Tage her ist. -delete loescht sie direkt - kein "rm" in einer Schleife noetig.
find "$BACKUP_DIR" -name "smartdesk-*.sql" -mtime +7 -delete

echo "==> Fertig ($(du -h "$BACKUP_FILE" | cut -f1))"

# Fuer automatische, regelmaessige Backups (statt von Hand aufrufen): auf dem
# Server "crontab -e" ausfuehren und z.B. diese Zeile eintragen (taeglich um
# 3 Uhr nachts):
#   0 3 * * * cd /root/SmartDesk && ./scripts/backup.sh >> /var/log/smartdesk-backup.log 2>&1
