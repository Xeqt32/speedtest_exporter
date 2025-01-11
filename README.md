# Speedtest Exporter

Ein Python-basierter Prometheus Exporter, der Internetgeschwindigkeits-Metriken über Speedtest.net sammelt.

## Features

- Regelmäßige Durchführung von Speedtests
- Prometheus-Metriken für:
  - Download-Geschwindigkeit
  - Upload-Geschwindigkeit
  - Ping/Latenz
  - ISP-Information
  - IP-Adresse
  - Server Info
- Health-Check Endpoint
- Docker-Support

## Voraussetzungen

- Docker
- oder Python 3.11+ mit speedtest-cli

## Installation

### Mit Docker

1. Repository klonen:
```bash
git clone [repository-url]
cd speedtest_exporter
```

2. Docker Image bauen:
```bash
docker build -t speedtest_exporter .
```

3. Container starten:
```bash
# Basis-Start
docker run -d -p 9798:9798 --name speedtest_exporter speedtest_exporter

# Mit angepassten Umgebungsvariablen
docker run -d \
  -p 9798:9798 \
  -e SCRAPE_INTERVAL=300 \
  -e SPEEDTEST_TIMEOUT=60 \
  -e TEST_SERVER=12345 \
  --name speedtest_exporter speedtest_exporter
```

### Ohne Docker

1. Repository klonen:
```bash
git clone [repository-url]
cd speedtest_exporter
```

2. Dependencies installieren:
```bash
pip install -r requirements.txt
```

3. Programm starten:
```bash
python app.py
```

## Verwendung

Der Exporter ist unter folgenden Endpoints erreichbar:

- Metriken: `http://localhost:9798/metrics`
- Health-Check: `http://localhost:9798/health`

### Umgebungsvariablen

Der Exporter kann über Umgebungsvariablen konfiguriert werden. Hier sind die verfügbaren Variablen und ihre Funktionen:

- `PORT`: Server Port (Standard: 9798)
  - Legt den Port fest, auf dem der Flask-Server läuft.
  
- `SCRAPE_INTERVAL`: Intervall zwischen Speedtests in Sekunden (Standard: 600)
  - Bestimmt, wie oft der Speedtest durchgeführt wird. Ein Wert von 300 bedeutet, dass alle 5 Minuten ein Test durchgeführt wird.

- `SPEEDTEST_TIMEOUT`: Timeout für einen einzelnen Speedtest in Sekunden (Standard: 60)
  - Legt die maximale Zeit fest, die für einen Speedtest gewartet wird. Wenn der Test länger dauert, wird er abgebrochen.

- `TEST_SERVER`: ID des Speedtest-Servers, der verwendet werden soll (z.B. `12345`).
  - Wenn angegeben, wird der Speedtest an diesem spezifischen Server durchgeführt.

- `NO_DOWNLOAD`: Wenn auf 'true' gesetzt, wird der Download-Test übersprungen.
  - Nützlich, wenn nur der Upload-Test benötigt wird.

- `NO_UPLOAD`: Wenn auf 'true' gesetzt, wird der Upload-Test übersprungen.
  - Nützlich, wenn nur der Download-Test benötigt wird.

- `USE_FALLBACK_TEST`: Wenn auf 'true' gesetzt, wird ein Fallback-Test ohne spezifischen Server durchgeführt, falls der Haupttest fehlschlägt.
  - Dies kann hilfreich sein, wenn der angegebene Testserver nicht verfügbar ist.

### Prometheus Konfiguration

Fügen Sie folgende Job-Konfiguration zu Ihrer `prometheus.yml` hinzu:

```yaml
scrape_configs:
  - job_name: 'speedtest'
    static_configs:
      - targets: ['localhost:9798']
```

## Metriken

- `speedtest_download_speed`: Download-Geschwindigkeit in Bits pro Sekunde
- `speedtest_upload_speed`: Upload-Geschwindigkeit in Bits pro Sekunde
- `speedtest_ping`: Latenz in Millisekunden
- `speedtest_isp`: Informationen über den Internet Service Provider
- `speedtest_public_ip`: Öffentliche IP-Adresse

## Empfohlene Prometheus-Konfiguration
```yaml
scrape_configs:
  - job_name: 'speedtest'
    scrape_interval: 5m      # Sollte größer/gleich SCRAPE_INTERVAL sein
    scrape_timeout: 90s      # Sollte größer als SPEEDTEST_TIMEOUT sein
    static_configs:
      - targets: ['localhost:9798']
```

**Wichtig**: 
- `scrape_interval` in Prometheus sollte größer oder gleich dem `SCRAPE_INTERVAL` der App sein.
- `scrape_timeout` in Prometheus sollte größer als der `SPEEDTEST_TIMEOUT` der App sein.

## Lizenz

GNU General Public License v3.0

Copyright (c) 2024 [Ihr Name]

Dieses Programm ist freie Software: Sie können es unter den Bedingungen der GNU General Public License, wie von der Free Software Foundation veröffentlicht, weitergeben und/oder modifizieren, entweder gemäß Version 3 der Lizenz oder (nach Ihrer Wahl) jeder späteren Version.

Die Veröffentlichung dieses Programms erfolgt in der Hoffnung, dass es Ihnen von Nutzen sein wird, aber OHNE IRGENDEINE GARANTIE, sogar ohne die implizite Garantie der MARKTREIFE oder der VERWENDBARKEIT FÜR EINEN BESTIMMTEN ZWECK. Details finden Sie in der GNU General Public License.

Wichtigste Bedingungen:
- Die Software muss kostenlos und Open Source bleiben.
- Änderungen müssen dokumentiert werden.
- Der ursprüngliche Autor muss genannt werden.
- Abgeleitete Werke müssen unter der gleichen Lizenz veröffentlicht werden.

Den vollständigen Lizenztext finden Sie unter: https://www.gnu.org/licenses/gpl-3.0.html
