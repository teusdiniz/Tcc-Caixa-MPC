# web/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # HOME
    path("", views.home, name="home"),

    # PAINEL
    path("painel/", views.painel_sem_sessao, name="painel_sem_sessao"),
    path("painel/<int:sessao_id>/", views.painel, name="painel"),

    # RETIRAR
    path("retirar/<int:sessao_id>/", views.retirar, name="retirar"),

    # confirmar retirada (gaveta a gaveta)
    path(
        "retirar-confirmar/<int:sessao_id>/",
        views.retirar_confirmar,
        name="retirar_confirmar",
    ),

    # rota antiga: /retirar/<id>/confirmar/ -> redireciona pra retirar-confirmar
    path(
        "retirar/<int:sessao_id>/confirmar/",
        views.retirar_confirmar_legacy,
        name="retirar_confirmar_legacy",
    ),

    # DEVOLVER (lista o que o colaborador tem pra devolver)
    path("devolver/<int:sessao_id>/", views.devolver, name="devolver"),

    # recebe o POST com as ferramentas selecionadas pra devolução
    path(
        "devolver/selecionar",
        views.devolver_selecionar,
        name="devolver_selecionar",
    ),

    # tela de confirmação por gaveta (gaveta_numero)
    path(
        "devolver/<int:sessao_id>/gaveta/<int:gaveta_numero>/",
        views.devolver_confirmar,
        name="devolver_confirmar",
    ),
]
