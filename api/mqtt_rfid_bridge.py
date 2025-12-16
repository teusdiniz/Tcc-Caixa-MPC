# api/mqtt_rfid_bridge.py

import json
import threading
import logging

import requests
import paho.mqtt.client as mqtt
from django.conf import settings

logger = logging.getLogger(__name__)

_mqtt_thread_started = False
_mqtt_client = None


def _on_connect(client, userdata, flags, reason_code, properties=None):
    try:
        code_int = int(reason_code)
    except Exception:
        code_int = getattr(reason_code, "value", reason_code)

    msg = f"[RFID BRIDGE] Conectado ao broker MQTT {settings.MQTT_CONFIG['HOST']}:{settings.MQTT_CONFIG['PORT']}, code={code_int}"
    print(msg)
    logger.info(msg)

    # >>> ADICIONA ESSE DEBUG AQUI <<<
    base = settings.MQTT_CONFIG.get("BASE", "tcc/caixa").rstrip("/")
    print(f"[RFID BRIDGE] BASE usada: {base}")
    logger.info(f"[RFID BRIDGE] BASE usada: {base}")

    topic = f"{base}/+/rfid/uid"

    client.subscribe(topic, qos=0)
    print(f"[RFID BRIDGE] Inscrito no tópico: {topic}")
    logger.info(f"[RFID BRIDGE] Inscrito no tópico: {topic}")

def _on_message(client, userdata, msg):
    """
    Chamado quando chega mensagem no tópico de RFID.
    """
    try:
        payload_str = msg.payload.decode("utf-8", errors="ignore")
    except Exception:
        payload_str = "<erro ao decodificar payload>"

    print(f"[RFID BRIDGE] Mensagem recebida em {msg.topic}: {payload_str}")
    logger.info(f"[RFID BRIDGE] Mensagem recebida em {msg.topic}: {payload_str}")

    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError as e:
        print(f"[RFID BRIDGE] JSON inválido: {e}")
        logger.exception("[RFID BRIDGE] JSON inválido")
        return

    # URL do Django (como você está rodando: python manage.py runserver 192.168.50.2:8000)
    base_url = "http://192.168.50.2:8000"
    url = f"{base_url}/api/nfc-tap/"

    try:
        resp = requests.post(url, json=data, timeout=5)
        print(f"[RFID BRIDGE] POST {url} -> {resp.status_code} {resp.text[:200]}")
        logger.info(f"[RFID BRIDGE] POST {url} -> {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        print(f"[RFID BRIDGE] Erro ao POST para Django: {e}")
        logger.exception("[RFID BRIDGE] Erro ao POST para Django")


def start_rfid_bridge_in_thread():
    """
    Inicia o cliente MQTT em uma thread separada (somente uma vez).
    """
    global _mqtt_thread_started, _mqtt_client

    if _mqtt_thread_started:
        print("[RFID BRIDGE] Já iniciado, ignorando nova chamada.")
        return

    _mqtt_thread_started = True

    host = settings.MQTT_CONFIG.get("HOST", "192.168.50.2")
    port = int(settings.MQTT_CONFIG.get("PORT", 1883))
    user = settings.MQTT_CONFIG.get("USER") or None
    pwd = settings.MQTT_CONFIG.get("PASS") or None

    print(f"[RFID BRIDGE] Iniciando bridge MQTT -> Django (broker={host}:{port})...")
    logger.info(f"[RFID BRIDGE] Iniciando bridge MQTT -> Django (broker={host}:{port})...")

    client = mqtt.Client()

    if user:
        client.username_pw_set(user, pwd)

    client.on_connect = _on_connect
    client.on_message = _on_message

    try:
        client.connect(host, port, keepalive=60)
    except Exception as e:
        print(f"[RFID BRIDGE] ERRO ao conectar no broker MQTT: {e}")
        logger.exception("[RFID BRIDGE] ERRO ao conectar no broker MQTT")
        return

    _mqtt_client = client

    th = threading.Thread(target=client.loop_forever, daemon=True)
    th.start()

    print("[RFID BRIDGE] Thread MQTT iniciada.")
    logger.info("[RFID BRIDGE] Thread MQTT iniciada.")
