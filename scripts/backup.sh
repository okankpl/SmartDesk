#!/usr/bin/env bash
# Sichert die Postgres-Datenbank in eine Datei mit Zeitstempel und entfernt
# Backups, die aelter als 7 Tage sind - im SmartDesk-Ordner auf dem Server
# ausfuehren (./scripts/backup.sh), idealerweise per Cron regelmaessig
# automatisch (siehe Kommentar ganz unten).
#
# "Wie lange werden alte Backups aufgehoben, bevor sie geloescht werden" nennt
# man eine Retention Policy - hier bewusst simpel (7 Tage, feste Zahl), damit
# die Festplatte des Servers nicht irgendwann von immer mehr Backups vollLAEUFT.
#
# Wiederherstellen (ueberschreibt die aktuelle Datenbank!):
#   docker compose -f docker-compose.prod.yml exec -T postgres \
#     sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backups/smartdesk-<zeitstempel>.sql
set -euo pipefail

# In den Projekt-Ordner wechseln (wie in deploy.sh): vorher wurde nur der
# Backup-Ordner relativ zum Skript bestimmt, "docker compose -f
# docker-compose.prod.yml" suchte die Datei aber im AKTUELLEN Ordner - von
# woanders aus gestartet, fand das Skript die Compose-Datei nicht.
cd "$(dirname "$0")/.."

BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/smartdesk-$TIMESTAMP.sql"

echo "==> Sichere Datenbank nach $BACKUP_FILE"
# Benutzer und Datenbank kommen aus den Umgebungsvariablen IM Postgres-
# Container (dieselben Werte wie in .env), statt fest "smartdesk" im Skript -
# bei anderen Werten in der Server-.env schlug das Backup sonst fehl.
# Die einfachen Anfuehrungszeichen um 'pg_dump ...' sorgen dafuer, dass
# $POSTGRES_USER erst im Container eingesetzt wird, nicht schon hier.
# Erst in eine ".partial"-Datei schreiben und nur bei Erfolg umbenennen:
# bricht pg_dump mittendrin ab, bleibt sonst eine halbe Datei liegen, die wie
# ein gueltiges Backup aussieht. trap ... ERR laeuft automatisch, falls ein
# Befehl fehlschlaegt (kurz bevor "set -e" das Skript beendet), und raeumt
# die halbe Datei dann weg.
# --clean --if-exists: das Backup beginnt mit "DROP ... IF EXISTS" fuer jede
# Tabelle - nur so laesst es sich in die BESTEHENDE Datenbank zurueckspielen
# (siehe "Wiederherstellen" oben), ohne an "existiert bereits" zu scheitern.
trap 'rm -f "$BACKUP_FILE.partial"' ERR
docker compose -f docker-compose.prod.yml exec -T postgres \
  sh -c 'pg_dump --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "$BACKUP_FILE.partial"
mv "$BACKUP_FILE.partial" "$BACKUP_FILE"

echo "==> Entferne Backups aelter als 7 Tage"
# find ... -mtime +7: findet Dateien, deren letzte Aenderung laenger als 7
# Tage her ist. -delete loescht sie direkt - kein "rm" in einer Schleife noetig.
find "$BACKUP_DIR" -name "smartdesk-*.sql" -mtime +7 -delete

echo "==> Fertig ($(du -h "$BACKUP_FILE" | cut -f1))"

# Hinweis: die Backups liegen auf DEMSELBEN Server wie die Datenbank. Faellt
# der Server komplett aus, sind beide weg - fuer echten Schutz regelmaessig
# eine Kopie an einen anderen Ort ziehen (z.B. per scp/rsync auf den eigenen
# Rechner oder in einen Cloud-Speicher).
#
# Fuer automatische, regelmaessige Backups (statt von Hand aufrufen): auf dem
# Server "crontab -e" ausfuehren und z.B. diese Zeile eintragen (taeglich um
# 3 Uhr nachts):
#   0 3 * * * /root/SmartDesk/scripts/backup.sh >> /var/log/smartdesk-backup.log 2>&1
