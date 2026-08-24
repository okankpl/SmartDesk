#!/usr/bin/env bash
# Wird AUF DEM SERVER ausgefuehrt (nicht lokal auf dem Entwicklungsrechner) -
# fasst die manuellen Schritte aus docs/deployment.md ("Laufender Betrieb:
# Update ausrollen") zu einem einzigen Befehl zusammen.
#
# Genau das ist eine typische DevOps-Taetigkeit: eine wiederholte manuelle
# Prozedur in ein Skript giessen, damit sie nicht bei jedem Mal aus dem
# Gedaechtnis nachgebaut werden muss und nie versehentlich ein Schritt
# vergessen wird (z.B. die Migration nach einem Deploy).
#
# Aufruf: ./scripts/deploy.sh   (im SmartDesk-Ordner auf dem Server)

# "set -e" (exit on error): bricht das Skript sofort ab, sobald IRGENDEIN
# Befehl einen Fehler-Exitcode liefert - ohne das wuerde z.B. bei einem
# fehlgeschlagenen "git pull" das Skript trotzdem weiterlaufen und am Ende
# eine kaputte/alte Version deployen, als waere nichts gewesen.
# "set -u" (nounset): bricht ab, wenn eine nicht gesetzte Variable benutzt
# wird - faengt Tippfehler in Variablennamen ab (z.B. $BACKUP_DIR statt
# $BACKUPDIR), die sonst stillschweigend als leerer String durchgehen wuerden.
# "set -o pipefail": bei einer Kette "befehl1 | befehl2" zaehlt sonst NUR der
# Exitcode des LETZTEN Befehls - schlaegt befehl1 fehl, faellt das ohne
# pipefail nicht auf, wenn befehl2 trotzdem erfolgreich durchlaeuft.
# Diese drei Optionen zusammen nennt man oft "Bash Strict Mode" - guter
# Standard-Kopf fuer praktisch jedes ernstgemeinte Bash-Skript.
set -euo pipefail

echo "==> Neuen Code holen"
git pull

echo "==> Frontend bauen (im Node-Container, kein Node auf dem Server noetig)"
docker run --rm -v "$(pwd)/frontend:/app" -w /app node:20 sh -c "npm ci && npx ng build --configuration production"

echo "==> Container neu bauen und starten"
docker compose -f docker-compose.prod.yml up -d --build

echo "==> Datenbank-Migrationen anwenden"
# "-T" deaktiviert ein Pseudo-Terminal fuer den Befehl - in einem Skript (ohne
# interaktives Terminal) sonst manchmal ein Fehlerquell, in einer normalen
# Shell-Sitzung braucht man es nicht.
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

echo "==> Fertig. Health-Check:"
curl -fsS "http://localhost:8000/health" && echo
