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
RUN useradd --create-home appuser
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
