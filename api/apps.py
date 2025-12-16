# api/apps.py

import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        """
        Chamado quando a app 'api' é inicializada.
        Aqui iniciamos o bridge MQTT -> Django em uma thread.
        """
        print("[RFID BRIDGE] ApiConfig.ready() chamado.")
        logger.info("[RFID BRIDGE] ApiConfig.ready() chamado.")

        from .mqtt_rfid_bridge import start_rfid_bridge_in_thread

        try:
            start_rfid_bridge_in_thread()
            print("[RFID BRIDGE] start_rfid_bridge_in_thread() chamado.")
            logger.info("[RFID BRIDGE] start_rfid_bridge_in_thread() chamado.")
        except Exception as e:
            logger.exception("[RFID BRIDGE] Erro ao iniciar bridge: %s", e)
            print(f"[RFID BRIDGE] ERRO ao iniciar bridge: {e}")
