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

# In den Projekt-Ordner wechseln, egal von wo aus das Skript gestartet wird -
# alle Pfade unten (docker-compose.prod.yml, frontend/) sind relativ dazu.
# "$(dirname "$0")" ist der Ordner dieses Skripts, "/.." eine Ebene hoeher.
cd "$(dirname "$0")/.."

# Eine kleine Shell-Funktion als Abkuerzung: "compose build" bedeutet
# "docker compose -f docker-compose.prod.yml build". "$@" reicht alle
# Argumente unveraendert weiter (auch solche mit Leerzeichen).
compose() {
  docker compose -f docker-compose.prod.yml "$@"
}

echo "==> Neuen Code holen"
git pull

echo "==> Frontend bauen (im Node-Container, kein Node auf dem Server noetig)"
# Dieselbe Node-Version wie in der CI, aus EINER Datei (frontend/.nvmrc) -
# vorher stand hier fest "node:20", mit dem Angular 22 gar nicht mehr startet.
NODE_VERSION="$(cat frontend/.nvmrc)"
docker run --rm -v "$(pwd)/frontend:/app" -w /app "node:${NODE_VERSION}" sh -c "npm ci && npx ng build --configuration production"

echo "==> Backend-Image bauen"
compose build backend

echo "==> Datenbank-Migrationen anwenden (mit dem NEUEN Image, bevor es live geht)"
# "run --rm" startet einen einmaligen Container aus dem gerade gebauten Image,
# fuehrt nur die Migration aus und entfernt ihn danach wieder. Die Migration
# laeuft bewusst VOR dem Umschalten: vorher lief der neue Code schon, waehrend
# die Datenbank noch das alte Schema hatte. Schlaegt die Migration fehl,
# bricht "set -e" hier ab - die bisherige Version laeuft dann unveraendert weiter.
compose run --rm backend alembic upgrade head

echo "==> Container mit der neuen Version starten"
compose up -d

echo "==> Health-Check (Backend, Datenbank und Login-Schutz)"
# Fragt /health/ready von INNERHALB des Backend-Containers ab. Vorher pruefte
# das Skript "curl http://localhost:8000/health" vom Server aus - der
# Backend-Port ist in Produktion aber bewusst gar nicht nach aussen
# freigegeben (siehe docker-compose.prod.yml), der Check schlug also IMMER
# fehl. Python statt curl, weil das schlanke python-Image kein curl enthaelt.
# Bis zu 10 Versuche im Abstand von 2 Sekunden: direkt nach "up -d" startet
# Uvicorn noch. "seq 1 10" erzeugt die Zahlen 1 bis 10 fuer die Schleife.
for attempt in $(seq 1 10); do
  if compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready', timeout=3)" 2>/dev/null; then
    echo "OK: Backend erreicht Datenbank und gemeinsamen Login-Schutz."
    exit 0
  fi
  echo "    noch nicht bereit (Versuch ${attempt}/10) ..."
  sleep 2
done

echo "FEHLER: /health/ready antwortet nicht. Logs ansehen mit:" >&2
echo "  docker compose -f docker-compose.prod.yml logs backend" >&2
exit 1
