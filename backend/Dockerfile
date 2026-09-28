FROM python:3.12-slim

WORKDIR /app

# Erst nur die Abhängigkeiten kopieren, damit Docker diesen Layer cachen kann,
# solange sich requirements.txt nicht ändert (schnellere Rebuilds).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Eigener, unprivilegierter Benutzer statt root: ohne diese Zeilen liefe
# Uvicorn im Container als root. Gelaenge ein Angriff ueber eine Luecke im
# Code oder in einer Abhaengigkeit, haette der Angreifer im Container sofort
# Administratorrechte - als "appuser" darf er dort deutlich weniger
# ("Principle of Least Privilege"). --create-home legt ein Home-Verzeichnis
# an, das manche Python-Tools fuer Cache-Dateien erwarten.
#
# Folge: appuser darf den Code in /app nur lesen, nicht veraendern - genau
# das ist gewollt. Der einzige Befehl, der Dateien ins Projekt schreibt
# (neue Migration per "alembic revision --autogenerate"), laeuft deshalb
# gezielt mit "docker compose exec -u root ..." (siehe README).
RUN useradd --create-home appuser
USER appuser

# pytest legt sonst einen Cache-Ordner (.pytest_cache) in /app an - das
# darf appuser nicht, jeder Testlauf endete mit einer Warnung. Im Container
# wird der Cache (z.B. fuer "nur zuletzt fehlgeschlagene Tests") nicht
# gebraucht, also abschalten statt dem Benutzer Schreibrechte zu geben.
ENV PYTEST_ADDOPTS="-p no:cacheprovider"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
