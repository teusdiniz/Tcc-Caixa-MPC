# api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("nfc-tap/", views.nfc_tap, name="nfc_tap"),

    # endpoint que o home.js usa
    path("status-frontend/", views.status_frontend, name="status_frontend"),

    # OPCIONAL: alias pra compatibilidade, se algum lugar ainda chamar /api/status
    path("status/", views.status_frontend, name="status"),

    path("sessoes/<int:sessao_id>/retiradas/",
         views.registrar_retirada,
         name="registrar_retirada"),

    path("sessoes/<int:sessao_id>/gaveta/<int:gaveta_numero>/confirmar-retirada/",
         views.confirmar_retirada_gaveta,
         name="confirmar_retirada_gaveta"),

    path("sessoes/<int:sessao_id>/devolucoes/",
         views.registrar_devolucao,
         name="registrar_devolucao"),

    path("sessoes/<int:sessao_id>/gaveta/<int:gaveta_numero>/confirmar-devolucao/",
         views.confirmar_devolucao_gaveta,
         name="confirmar_devolucao_gaveta"),
]
