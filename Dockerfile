# Verwende ein leichtes Python-Image
FROM python:3.11-slim

# Setze Arbeitsverzeichnis
WORKDIR /app

# Installiere systemabhängige Abhängigkeiten
RUN apt-get update && apt-get install -y \
    speedtest-cli \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Kopiere Abhängigkeits- und Quellcode-Dateien
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Setze Umgebungsvariablen für Port
ENV PORT=9798

# Exponiere den Port
EXPOSE 9798

# Starte die Anwendung
CMD ["python", "app.py"]
