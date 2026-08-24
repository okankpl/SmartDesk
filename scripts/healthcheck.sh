#!/usr/bin/env bash
# Minimalstes Monitoring-Beispiel: prueft, ob /api/health mit Erfolg antwortet,
# schreibt bei einem Fehlschlag eine Zeile ins System-Log und beendet sich mit
# einem Fehler-Exitcode (wichtig, damit z.B. ein Cron-Job merkt, dass etwas
# schiefging - siehe Kommentar ganz unten).
#
# Echte Systeme nutzen dafuer meist fertige Tools (Uptime Kuma fuer simples
# Self-Hosting, Prometheus+Grafana fuer groessere Systeme mit Metriken/
# Dashboards, Sentry fuer Fehler-Tracking im Code selbst) - das Grundprinzip
# dahinter ist aber genau dieses: regelmaessig automatisiert fragen "geht's
# dem System noch gut" und reagieren, wenn nicht, statt zu warten, bis sich
# ein Nutzer beschwert.
set -euo pipefail

# "${1:-...}": nimmt das erste Kommandozeilen-Argument, falls eins mitgegeben
# wurde, sonst den Wert nach dem ":-" als Standardwert - so funktioniert das
# Skript auch ohne Argument (mit einem sinnvollen Default) UND laesst sich bei
# Bedarf gegen eine andere URL testen: ./scripts/healthcheck.sh https://andere-domain/api/health
URL="${1:-https://smartdesk.example.com/api/health}"

# curl -f: behandelt HTTP-Fehler-Statuscodes (4xx/5xx) selbst als Fehler
# (ohne -f waere ein 500er trotzdem ein "erfolgreicher" curl-Aufruf, nur mit
# einer Fehlerseite als Inhalt). -s: unterdrueckt den Fortschrittsbalken.
# -S: zeigt trotzdem eine Fehlermeldung, falls -s sonst auch die unterdruecken wuerde.
if curl -fsS "$URL" > /dev/null; then
  echo "OK: $URL antwortet"
else
  # logger schreibt in das System-Log (journalctl -t smartdesk-healthcheck
  # zeigt es auf dem Server an) - so verschwindet ein Ausfall nicht spurlos,
  # auch wenn gerade niemand vor dem Terminal sitzt.
  logger -t smartdesk-healthcheck "ALARM: $URL antwortet nicht"
  echo "FEHLER: $URL antwortet nicht" >&2
  exit 1
fi

# Als Cron-Job alle 5 Minuten pruefen (auf dem Server, "crontab -e"):
#   */5 * * * * /root/SmartDesk/scripts/healthcheck.sh
