#!/usr/bin/env python3
import os
import subprocess
import logging
from datetime import datetime
from flask import Flask, jsonify, render_template_string
from prometheus_client import Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from threading import Thread, Event
import json
import signal

# Konfiguration über Umgebungsvariablen
TEST_SERVER = os.getenv('TEST_SERVER', '')
SCRAPE_INTERVAL = int(os.getenv('SCRAPE_INTERVAL', '600'))  # in Sekunden
SPEEDTEST_TIMEOUT = int(os.getenv('SPEEDTEST_TIMEOUT', '60'))  # in Sekunden
NO_DOWNLOAD = os.getenv('NO_DOWNLOAD', 'false').lower() == 'true'
NO_UPLOAD = os.getenv('NO_UPLOAD', 'false').lower() == 'true'
USE_FALLBACK_TEST = os.getenv('USE_FALLBACK_TEST', 'false').lower() == 'true'

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
test_server_metric = Gauge('speedtest_test_server_id', 'Verwendeter Testserver (ID)')
speedtest_up = Gauge('speedtest_up', 'Speedtest Status (1=erfolgreich, 0=Fehler)')
test_time = Gauge('speedtest_test_time', 'Zeit des letzten Tests Unix Timestamp')
bytes_sent = Gauge('speedtest_bytes_sent', 'Anzahl der gesendeten Bytes')
bytes_received = Gauge('speedtest_bytes_received', 'Anzahl der empfangenen Bytes')
isp_rating = Gauge('speedtest_isp_rating', 'ISP Bewertung')
client_lat = Gauge('speedtest_client_latitude', 'Breitengrad des Clients')
client_lon = Gauge('speedtest_client_longitude', 'Längengrad des Clients')

# Zusätzliche Metriken für Serverdaten
server_d = Gauge('speedtest_server_distance_km', 'Entfernung zum Server in km')
server_latency = Gauge('speedtest_server_latency_ms', 'Latenz zum Server in ms')

# Info Metriken für Client und Server
client_info = Info('speedtest_client_info', 'Informationen über den Client')
server_info = Info('speedtest_server_info', 'Informationen über den verwendeten Server')

stop_event = Event()

def build_speedtest_command():
    """
    Baut den Speedtest-Befehl basierend auf den Umgebungsvariablen auf.
    """
    cmd = ['speedtest-cli', '--json']
    
    if TEST_SERVER:
        cmd.extend(['--server', str(TEST_SERVER)])
    if NO_DOWNLOAD:
        cmd.append('--no-download')
    if NO_UPLOAD:
        cmd.append('--no-upload')
    
    return cmd

def execute_speedtest(cmd):
    """
    Führt den Speedtest aus und gibt die JSON-Ausgabe zurück.
    """
    logger.info(f"Speedtest-Befehl: {' '.join(cmd)}")
    
    result = subprocess.run(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True, 
        check=True,
        timeout=SPEEDTEST_TIMEOUT
    )
    
    if not result.stdout:
        raise ValueError('Keine Ausgabe vom Speedtest-Befehl erhalten.')
    
    return json.loads(result.stdout)

def update_metrics(data):
    """
    Aktualisiert die Prometheus-Metriken basierend auf den Speedtest-Daten.
    """
    # Numerische Metriken
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
    client_lat.set(float(data.get('client', {}).get('lat', 0)))
    client_lon.set(float(data.get('client', {}).get('lon', 0)))
    
    server_d.set(float(data.get('server', {}).get('d', 0)))
    server_latency.set(float(data.get('server', {}).get('latency', 0)))

    # Client Info
    client_info_data = data.get('client', {})
    client_info.info({
        'ip_address': client_info_data.get('ip', '0.0.0.0'),
        'isp': client_info_data.get('isp', 'Unknown'),
        'latitude': client_info_data.get('lat', '0'),
        'longitude': client_info_data.get('lon', '0'),
        'isprating': client_info_data.get('isprating', '0'),
        'rating': client_info_data.get('rating', '0'),
        'ispdlavg': client_info_data.get('ispdlavg', '0'),
        'ispulavg': client_info_data.get('ispulavg', '0'),
        'loggedin': client_info_data.get('loggedin', '0'),
        'country': client_info_data.get('country', 'Unknown')
    })

    # Server Info
    server_data = data.get('server', {})
    server_info.info({
        'url': server_data.get('url', ''),
        'lat': server_data.get('lat', ''),
        'lon': server_data.get('lon', ''),
        'name': server_data.get('name', ''),
        'country': server_data.get('country', ''),
        'cc': server_data.get('cc', ''),
        'sponsor': server_data.get('sponsor', ''),
        'id': server_data.get('id', ''),
        'host': server_data.get('host', ''),
        'd': server_data.get('d', ''),
        'latency': server_data.get('latency', '')
    })

def log_server_info(data):
    """
    Protokolliert Informationen über den verwendeten Server.
    """
    server_used = data.get('server', {}).get('id', 'Unknown')
    server_name = data.get('server', {}).get('name', 'Unknown')
    logger.info(f'Verwendeter Server: ID={server_used}, Name={server_name}')

def perform_speedtest():
    """
    Führt den Speedtest durch, einschließlich Fallback-Logik, falls aktiviert.
    """
    try:
        cmd = build_speedtest_command()
        data = execute_speedtest(cmd)
        logger.info(f'Speedtest Rohdaten: {data}')
        update_metrics(data)
        log_server_info(data)
        logger.info('Speedtest erfolgreich abgeschlossen.')
    except (subprocess.CalledProcessError, ValueError) as e:
        logger.error(f'Speedtest fehlgeschlagen: {e}')
        if USE_FALLBACK_TEST and TEST_SERVER:
            logger.info('Versuche Fallback-Test ohne Server-ID...')
            try:
                fallback_cmd = build_speedtest_command()
                # Entfernen der '--server' Option, um den Fallback zu erzwingen
                if '--server' in fallback_cmd:
                    server_index = fallback_cmd.index('--server')
                    del fallback_cmd[server_index:server_index + 2]
                data = execute_speedtest(fallback_cmd)
                logger.info(f'Fallback Speedtest Rohdaten: {data}')
                update_metrics(data)
                log_server_info(data)
                logger.info('Fallback Speedtest erfolgreich abgeschlossen.')
            except Exception as fallback_e:
                logger.error(f'Fallback Speedtest fehlgeschlagen: {fallback_e}')
                speedtest_up.set(0)
        else:
            speedtest_up.set(0)
    except json.JSONDecodeError as e:
        logger.error('Fehler beim Dekodieren der JSON-Ausgabe.')
        logger.error(f'Rohdaten: {e}')
        speedtest_up.set(0)
    except Exception as e:
        logger.exception('Ein unerwarteter Fehler ist aufgetreten während des Speedtests.')
        speedtest_up.set(0)

def run_speedtest():
    while not stop_event.is_set():
        perform_speedtest()
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