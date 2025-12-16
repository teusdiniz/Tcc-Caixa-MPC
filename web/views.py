import json

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from inventario.models import Ferramenta, Gaveta
from operacoes.models import SessaoUso, MovimentacaoFerramenta
from django.db import models
from django.db.models import Exists, OuterRef, Subquery

from hardware.mqtt_client import publish_run_command
from django.views.decorators.http import require_POST
from django.contrib import messages


def home(request: HttpRequest) -> HttpResponse:
    """
    Tela inicial (home.html).
    Fica perguntando /api/status-frontend pra saber se existe sessão ativa.
    """
    return render(request, "web/home.html")


def painel_sem_sessao(request: HttpRequest) -> HttpResponse:
    """
    /painel/ sem ID:
      - se existir alguma sessão "A" em andamento, redireciona para /painel/<id>/
      - se não existir, volta pra home.
    Evita 404 e redireções estranhas.
    """
    sessao = (
        SessaoUso.objects
        .filter(status="A")
        .order_by("-iniciado_em")
        .first()
    )

    if sessao:
        return redirect("painel", sessao_id=sessao.id)

    return redirect("home")


def painel(request: HttpRequest, sessao_id: int) -> HttpResponse:
    """
    Tela principal da sessão.
    Mostra:
      - nome do colaborador
      - botão RETIRAR / DEVOLVER
    """
    sessao = get_object_or_404(
        SessaoUso.objects.select_related("colaborador"),
        id=sessao_id,
    )

    proxima_gaveta = (
        MovimentacaoFerramenta.objects
        .filter(
            sessao=sessao,
            tipo="R",               # retirada
            confirmado_visao=False  # ainda não confirmada pela visão
        )
        .order_by("gaveta_numero")
        .values_list("gaveta_numero", flat=True)
        .first()
    )

    context = {
        "sessao_id": sessao.id,
        "funcionario": sessao.colaborador.nome,
        "gaveta_atual": proxima_gaveta,
    }

    return render(request, "web/painel.html", context)


def retirar(request: HttpRequest, sessao_id: int) -> HttpResponse:
    """
    Tela de escolha de ferramentas para retirada.

    Regra:
    - A ferramenta aparece aqui se o último movimento confirmado dela
      NÃO for uma retirada (ou seja, está na gaveta).
      last_tipo in [None, "D"]
    """
    sessao = get_object_or_404(SessaoUso, id=sessao_id)

    # Subquery: último movimento confirmado (R ou D) dessa ferramenta
    last_mov_qs = (
        MovimentacaoFerramenta.objects
        .filter(
            ferramenta=OuterRef("pk"),
            confirmado_visao=True,
        )
        .order_by("-criado_em")
    )

    qs = (
        Ferramenta.objects
        .select_related("gaveta")
        .filter(ativa=True)
        .annotate(
            last_tipo=Subquery(last_mov_qs.values("tipo")[:1]),
        )
        .filter(
            models.Q(last_tipo__isnull=True) | models.Q(last_tipo="D")
        )
        .order_by("gaveta__numero", "posicao", "nome")
    )

    gavetas_dict = {}
    for f in qs:
        nome_gaveta = f.gaveta.nome if f.gaveta else "Sem gaveta"
        gavetas_dict.setdefault(nome_gaveta, []).append(f)

    gavetas = sorted(gavetas_dict.items(), key=lambda item: item[0])

    context = {
        "sessao_id": sessao.id,
        "gavetas": gavetas,
    }
    return render(request, "web/retirar.html", context)


def devolver(request: HttpRequest, sessao_id: int) -> HttpResponse:
    """
    Tela de devolução:
    - mostra apenas as ferramentas cujo último movimento confirmado do colaborador foi RETIRADA.
    """
    sessao = get_object_or_404(
        SessaoUso.objects.select_related("colaborador"),
        id=sessao_id,
    )
    colaborador = sessao.colaborador

    # último movimento confirmado por ferramenta para esse colaborador
    last_mov_qs = (
        MovimentacaoFerramenta.objects
        .filter(
            ferramenta=OuterRef("pk"),
            sessao__colaborador=colaborador,
            confirmado_visao=True,
        )
        .order_by("-criado_em")
    )

    # ferramentas cujo último movimento foi "R" (retirada)
    ferramentas = (
        Ferramenta.objects
        .select_related("gaveta")
        .filter(ativa=True)
        .annotate(last_tipo=Subquery(last_mov_qs.values("tipo")[:1]))
        .filter(last_tipo="R")
        .order_by("gaveta__numero", "nome")
    )

    vazio = not ferramentas.exists()

    grupos = []
    if not vazio:
        gavetas_dict = {}
        for f in ferramentas:
            nome_gaveta = f.gaveta.nome if f.gaveta else "Sem gaveta"
            gavetas_dict.setdefault(nome_gaveta, []).append(f)

        for nome_gaveta, itens in gavetas_dict.items():
            grupos.append({
                "gaveta": nome_gaveta,
                "itens": [
                    {"id": f.id, "nome": f.nome}
                    for f in itens
                ],
            })

    context = {
        "sessao_id": sessao.id,
        "vazio": vazio,
        "grupos": grupos,
    }
    return render(request, "web/devolver.html", context)


@csrf_exempt
@require_POST
def devolver_selecionar(request):
    """
    Recebe via POST (JSON) a lista de ferramentas selecionadas para devolução.
    Cria as MovimentacaoFerramenta(tipo='D') e devolve a URL da
    primeira gaveta que deve ser exibida na tela de confirmação.
    """
    # sessao_id vem pela querystring: /devolver/selecionar?sessao_id=39
    sessao_id = request.GET.get("sessao_id")
    if not sessao_id:
        return JsonResponse({"error": "sessao_id obrigatório"}, status=400)

    sessao = get_object_or_404(SessaoUso, id=sessao_id)

    # corpo JSON com {"ferramentas_ids": [1, 2, 3]}
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    ids = data.get("ferramentas_ids", [])
    if not ids:
        return JsonResponse(
            {"error": "Nenhuma ferramenta selecionada"},
            status=400,
        )

    # Busca as ferramentas selecionadas (junto com a gaveta)
    ferramentas = (
        Ferramenta.objects
        .select_related("gaveta")
        .filter(id__in=ids, ativa=True)
    )

    # Agrupa por número da gaveta
    por_gaveta = {}
    for f in ferramentas:
        if not f.gaveta:
            # se tiver ferramenta sem gaveta, pula
            continue
        numero = f.gaveta.numero or 0
        por_gaveta.setdefault(numero, []).append(f)

    if not por_gaveta:
        return JsonResponse(
            {"error": "Nenhuma ferramenta com gaveta válida encontrada"},
            status=400,
        )

    # Cria as movimentações de devolução e manda abrir as gavetas
    for numero, lista in por_gaveta.items():
        for f in lista:
            MovimentacaoFerramenta.objects.create(
                sessao=sessao,
                ferramenta=f,
                tipo="D",
                gaveta_numero=numero,
                confirmado_visao=False,
            )

        # Comando para abrir a gaveta via MQTT
        # (mesma função que você já está usando no fluxo de retirada)
        publish_run_command("abrir_gaveta", {"gaveta": numero})

    # Define qual gaveta vai aparecer primeiro na tela de confirmação
    proxima_gaveta = sorted(por_gaveta.keys())[0]

    next_url = reverse(
        "devolver_confirmar",
        kwargs={"sessao_id": sessao.id, "gaveta_numero": proxima_gaveta},
    )

    return JsonResponse({"ok": True, "next_url": next_url})

def devolver_confirmar(request, sessao_id, gaveta_numero):
    sessao = get_object_or_404(SessaoUso, id=sessao_id)

    movs = (
        MovimentacaoFerramenta.objects
        .select_related("ferramenta", "ferramenta__gaveta")
        .filter(
            sessao=sessao,
            tipo="D",
            gaveta_numero=gaveta_numero,
            confirmado_visao=False,
        )
        .order_by("ferramenta__nome")
    )

    if not movs:
        return redirect("painel", sessao_id=sessao.id)

    # 🔹 AQUI: manda ABRIR a gaveta para devolução
    device_alias = getattr(settings, "READER_ID", "rasp-01")
    publish_run_command(device_alias, f"abrir_gaveta_{int(gaveta_numero)}")

    grupo = {
        "gaveta": f"Gaveta {gaveta_numero}",
        "itens": [
            {
                "id": m.ferramenta.id,
                "nome": m.ferramenta.nome,
            }
            for m in movs
        ],
    }

    context = {
        "sessao": sessao,
        "sessao_id": sessao.id,
        "gaveta_numero": gaveta_numero,
        "grupos": [grupo],
    }
    return render(request, "web/devolver_confirmar.html", context)

def retirar_confirmar(request: HttpRequest, sessao_id: int) -> HttpResponse:
    """
    Tela que mostra as ferramentas selecionadas e permite confirmar
    a retirada da gaveta atual (a próxima gaveta com movimentação pendente).
    """
    sessao = get_object_or_404(
        SessaoUso.objects.select_related("colaborador"),
        id=sessao_id,
    )

    # próxima gaveta com retirada pendente
    proxima_gaveta = (
        MovimentacaoFerramenta.objects
        .filter(
            sessao=sessao,
            tipo="R",
            confirmado_visao=False,
        )
        .order_by("gaveta_numero")
        .values_list("gaveta_numero", flat=True)
        .first()
    )

    # se não tiver mais nada pra confirmar, volta pro painel
    if proxima_gaveta is None:
        return redirect("painel", sessao_id=sessao.id)

    movs = (
        MovimentacaoFerramenta.objects
        .filter(
            sessao=sessao,
            tipo="R",
            confirmado_visao=False,
            gaveta_numero=proxima_gaveta,
        )
        .select_related("ferramenta")
    )

    grupos = [{
        "gaveta": f"Gaveta {proxima_gaveta}",
        "itens": [
            {"nome": m.ferramenta.nome}
            for m in movs
        ],
    }]

    context = {
        "sessao_id": sessao.id,
        "gaveta_atual": proxima_gaveta,
        "grupos": grupos,
    }
    return render(request, "web/retirar_confirmar.html", context)


def retirar_confirmar_legacy(request: HttpRequest, sessao_id: int) -> HttpResponse:
    """
    Compatibilidade: se alguém chamar /retirar/<id>/confirmar/,
    redireciona para a rota oficial /retirar-confirmar/<id>/.
    """
    return redirect("retirar_confirmar", sessao_id=sessao_id)
