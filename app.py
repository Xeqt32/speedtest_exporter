#!/usr/bin/env python3
import os
import subprocess
import logging
from datetime import datetime
from flask import Flask, jsonify, render_template_string
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST, Info
from threading import Thread, Event
import json
import signal

# Konfiguration über Umgebungsvariablen
TEST_SERVER = os.getenv('TEST_SERVER', '')
SCRAPE_INTERVAL = int(os.getenv('SCRAPE_INTERVAL', '600'))  # in Sekunden
SPEEDTEST_TIMEOUT = int(os.getenv('SPEEDTEST_TIMEOUT', '60'))  # in Sekunden
NO_DOWNLOAD = os.getenv('NO_DOWNLOAD', 'false').lower() == 'true'
NO_UPLOAD = os.getenv('NO_UPLOAD', 'false').lower() == 'true'

# Logger konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask-Anwendung initialisieren
app = Flask(__name__)

# Prometheus Metriken
download_speed = Gauge('speedtest_download_speed', 'Download-Geschwindigkeit in Mbit/s')
upload_speed = Gauge('speedtest_upload_speed', 'Upload-Geschwindigkeit in Mbit/s')
latency = Gauge('speedtest_latency', 'Latenz in ms')
jitter = Gauge('speedtest_jitter', 'Jitter in ms')
test_server_metric = Gauge('speedtest_test_server', 'Verwendeter Testserver (ID)')
speedtest_up = Gauge('speedtest_up', 'Speedtest Status (1=erfolgreich, 0=Fehler)')
test_time = Gauge('speedtest_test_time', 'Zeit des letzten Tests Unix Timestamp')
bytes_sent = Gauge('speedtest_bytes_sent', 'Anzahl der gesendeten Bytes')
bytes_received = Gauge('speedtest_bytes_received', 'Anzahl der empfangenen Bytes')
isp_rating = Gauge('speedtest_isp_rating', 'ISP Bewertung')
client_lat = Gauge('speedtest_client_latitude', 'Breitengrad des Clients')
client_lon = Gauge('speedtest_client_longitude', 'Längengrad des Clients')

client_info = Info('speedtest_client_info', 'Informationen über den Client')

stop_event = Event()

def run_speedtest():
    while not stop_event.is_set():
        try:
            logger.info('Starte Speedtest...')
            cmd = ['speedtest-cli', '--json']
            if TEST_SERVER:
                cmd.append(['--server-id', TEST_SERVER])
            if NO_DOWNLOAD:
                cmd.append('--no-download')
            if NO_UPLOAD:
                cmd.append('--no-upload')

            # Protokolliere den gesamten Befehl vor der Ausführung
            logger.info(f"Speedtest-Befehl: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                check=True,
                timeout=SPEEDTEST_TIMEOUT
            )
            data = json.loads(result.stdout)

            # Debug-Log
            logger.info(f'Speedtest Rohdaten: {data}')

            # Metriken aktualisieren
            download_speed.set(data.get('download', 0) / 1e6)  # Bytes/s zu Mbit/s
            upload_speed.set(data.get('upload', 0) / 1e6)      # Bytes/s zu Mbit/s
            latency.set(data.get('ping', 0))                    # Latenz in ms
            jitter.set(data.get('jitter', 0))                    # Jitter in ms
            test_server_metric.set(data.get('server', {}).get('id', 0))  # Testserver-ID
            speedtest_up.set(1)                                   # Status auf erfolgreich setzen
            test_time.set(datetime.strptime(data.get('timestamp'), "%Y-%m-%dT%H:%M:%S.%fZ").timestamp())  # Zeit des letzten Tests
            bytes_sent.set(data.get('bytes_sent', 0))
            bytes_received.set(data.get('bytes_received', 0))
            isp_rating.set(float(data.get('client', {}).get('isprating', 0)))

            # IP und ISP als Labels setzen
            client_ip = str(data.get('client', {}).get('ip', '0.0.0.0'))
            client_isp = str(data.get('client', {}).get('isp', 'Unknown'))

            # Setze die Info-Metriken
            client_info.info({
                'ip_address': client_ip,
                'isp': client_isp,
                'latitude': data.get('client', {}).get('lat', 0),
                'longitude': data.get('client', {}).get('lon', 0)
            })

            # Zusätzliche Logs zur Verifizierung des verwendeten Servers
            server_used = data.get('server', {}).get('id', 'Unknown')
            server_name = data.get('server', {}).get('name', 'Unknown')
            logger.info(f'Verwendeter Server: ID={server_used}, Name={server_name}')

            logger.info('Speedtest erfolgreich abgeschlossen.')
        except subprocess.CalledProcessError as e:
            logger.error(f'Speedtest fehlgeschlagen: {e.stderr}')
            speedtest_up.set(0)  # Status auf Fehler setzen
        except Exception as e:
            logger.exception('Ein unerwarteter Fehler ist aufgetreten während des Speedtests.')
            speedtest_up.set(0)  # Status auf Fehler setzen
        finally:
            stop_event.wait(SCRAPE_INTERVAL)  # Wartezeit zwischen den Tests

@app.route('/')
def index():
    html = """
    <h1>Speedtest Prometheus Exporter</h1>
    <ul>
        <li><a href="/metrics">Metrics</a></li>
        <li><a href="/health">Health</a></li>
    </ul>
    """
    return render_template_string(html)

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/health')
def health():
    current_status = speedtest_up._value.get()
    health_status = {
        "status": "UP" if current_status == 1 else "DOWN",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    return jsonify(health_status), 200 if current_status == 1 else 500

def start_speedtest_thread():
    thread = Thread(target=run_speedtest)
    thread.daemon = True
    thread.start()

def shutdown_handler(signum, frame):
    logger.info('Shutdown Signal empfangen...')
    stop_event.set()

if __name__ == '__main__':
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    
    # Starte den Speedtest-Thread
    start_speedtest_thread()
    
    # Starte den Flask-Webserver
    port = int(os.getenv('PORT', '9798'))
    logger.info(f'Starte Flask auf Port {port}')
    app.run(host='0.0.0.0', port=port)
