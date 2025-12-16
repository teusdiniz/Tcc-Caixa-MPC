import json
import os
import time

import paho.mqtt.client as mqtt
import requests

# ===== CONFIGURAÇÕES BÁSICAS =====
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "") or None
MQTT_PASS = os.getenv("MQTT_PASS", "") or None

# tópico que a Rock Pi está publicando
MQTT_TOPIC = os.getenv(
    "CAIXA_RFID_TOPIC",
    "tcc/caixa/+/rfid/uid",  # wildcard no meio
)

# endpoint Django que você JÁ tem
API_NFC_TAP_URL = os.getenv(
    "CAIXA_API_NFC_TAP",
    "http://127.0.0.1:8000/api/nfc-tap/",
)


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[RFID] Conectado ao broker MQTT com código {rc}")
    if rc == 0:
        print(f"[RFID] Assinando tópico: {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC)
    else:
        print("[RFID] Falha ao conectar ao broker")


def on_message(client, userdata, msg):
    print(f"[RFID] Mensagem em {msg.topic}: {msg.payload!r}")
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception as e:
        print("[RFID] Payload inválido:", e)
        return

    # Aqui você simplesmente repassa o JSON para o Django
    try:
        resp = requests.post(API_NFC_TAP_URL, json=payload, timeout=5)
    except Exception as e:
        print("[RFID] Erro ao chamar API nfc_tap:", e)
        return

    print(f"[RFID] Resposta API {resp.status_code}: {resp.text}")

    # Se quiser, você pode usar a resposta pra ligar LED etc.
    # data = resp.json() (se status 201/403) e mandar MQTT "led_erro" ou "led_ok"


def main():
    client = mqtt.Client()
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[RFID] Conectando em {MQTT_HOST}:{MQTT_PORT}...")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)

    client.loop_start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[RFID] Encerrando listener...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
