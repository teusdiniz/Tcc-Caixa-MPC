import json
import logging
import time

import paho.mqtt.client as mqtt
from django.conf import settings

logger = logging.getLogger(__name__)


def publish_run_command(
    reader_id: str,
    alias: str,
    args=None,
    mode: str = "fg",
    timeout_s: float = 45.0,
):
    """
    Publica um comando para o runner da Rock Pi no tópico:
        tcc/caixa/{reader_id}/run

    Usa loop_start/loop_stop para garantir que o pacote MQTT
    realmente seja enviado antes de desconectar.
    """
    if args is None:
        args = []

    cfg = getattr(settings, "MQTT_CONFIG", {})
    host = cfg.get("HOST", "127.0.0.1")
    port = int(cfg.get("PORT", 1883))
    user = cfg.get("USER") or None
    password = cfg.get("PASS") or ""

    topic = f"tcc/caixa/{reader_id}/run"

    # req_id pode ser qualquer string única pra log/ACK
    req_id = f"sessao-{alias}-{int(time.time())}"

    payload = {
        "req_id": req_id,
        "alias": alias,
        "args": args,
        "mode": mode,         # "fg" ou "bg"
        "timeout_s": timeout_s,
    }

    client = mqtt.Client()
    if user:
        client.username_pw_set(user, password)

    try:
        client.connect(host, port, 60)

        # Inicia o loop de rede em background
        client.loop_start()

        # Publica com QoS 1
        info = client.publish(topic, json.dumps(payload), qos=1)

        # Espera o envio/ack da publicação (com timeout só pra não travar infinito)
        info.wait_for_publish(timeout=2)

        # Dá um tempinho pra garantir flush
        time.sleep(0.1)

        client.loop_stop()
        client.disconnect()

        logger.info("MQTT RUN publicado em %s: %s", topic, payload)
        return {"ok": True, "topic": topic, "payload": payload}
    except Exception as e:
        logger.error("Erro ao publicar MQTT RUN em %s: %s", topic, e)
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:
            pass
        return {"ok": False, "topic": topic, "error": str(e), "payload": payload}
