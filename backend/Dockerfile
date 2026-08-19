FROM python:3.12-slim

WORKDIR /app

# Erst nur die Abhängigkeiten kopieren, damit Docker diesen Layer cachen kann,
# solange sich requirements.txt nicht ändert (schnellere Rebuilds).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
