# Speedtest Prometheus Exporter

Ein Python-basierter Prometheus Exporter, der Internetgeschwindigkeits-Metriken über Speedtest.net sammelt.

## Features

- Regelmäßige Durchführung von Speedtests
- Prometheus-Metriken für:
  - Download-Geschwindigkeit
  - Upload-Geschwindigkeit
  - Ping/Latenz
  - ISP-Information (gehasht)
  - IP-Adresse (gehasht)
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
cd speedtest-exporter
```

2. Docker Image bauen:
```bash
docker build -t speedtest-exporter .
```

3. Container starten:
```bash
# Basis-Start
docker run -d -p 9798:9798 --name speedtest-exporter speedtest-exporter

# Mit angepassten Umgebungsvariablen
docker run -d \
  -p 9798:9798 \
  -e SCRAPE_INTERVAL=300 \
  -e SPEEDTEST_TIMEOUT=60 \
  --name speedtest-exporter speedtest-exporter
```

### Ohne Docker

1. Repository klonen:
```bash
git clone [repository-url]
cd speedtest-exporter
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
- `speedtest_isp`: Hash des Internet Service Providers
- `speedtest_public_ip`: Hash der öffentlichen IP-Adresse

## Umgebungsvariablen

- `PORT`: Server Port (Standard: 9798)
- `SCRAPE_INTERVAL`: Intervall zwischen Speedtests in Sekunden (Standard: 300)
- `SPEEDTEST_TIMEOUT`: Timeout für einen einzelnen Speedtest in Sekunden (Standard: 60)

### Empfohlene Prometheus-Konfiguration
```yaml
scrape_configs:
  - job_name: 'speedtest'
    scrape_interval: 5m      # Sollte größer/gleich SCRAPE_INTERVAL sein
    scrape_timeout: 90s      # Sollte größer als SPEEDTEST_TIMEOUT sein
    static_configs:
      - targets: ['localhost:9798']
```

**Wichtig**: 
- `scrape_interval` in Prometheus sollte größer oder gleich dem `SCRAPE_INTERVAL` der App sein
- `scrape_timeout` in Prometheus sollte größer als der `SPEEDTEST_TIMEOUT` der App sein

## Lizenz

GNU General Public License v3.0

Copyright (c) 2024 [Ihr Name]

Dieses Programm ist freie Software: Sie können es unter den Bedingungen der GNU General Public License, wie von der Free Software Foundation veröffentlicht, weitergeben und/oder modifizieren, entweder gemäß Version 3 der Lizenz oder (nach Ihrer Wahl) jeder späteren Version.

Die Veröffentlichung dieses Programms erfolgt in der Hoffnung, dass es Ihnen von Nutzen sein wird, aber OHNE IRGENDEINE GARANTIE, sogar ohne die implizite Garantie der MARKTREIFE oder der VERWENDBARKEIT FÜR EINEN BESTIMMTEN ZWECK. Details finden Sie in der GNU General Public License.

Wichtigste Bedingungen:
- Die Software muss kostenlos und Open Source bleiben
- Änderungen müssen dokumentiert werden
- Der ursprüngliche Autor muss genannt werden
- Abgeleitete Werke müssen unter der gleichen Lizenz veröffentlicht werden

Den vollständigen Lizenztext finden Sie unter: https://www.gnu.org/licenses/gpl-3.0.html
