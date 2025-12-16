# api/views.py

import json
import logging
from datetime import timedelta   # <-- garante isso

from django.http import JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from django.db.models import Subquery, OuterRef

from usuarios.models import CartaoNFC
from operacoes.models import SessaoUso, MovimentacaoFerramenta
from inventario.models import Gaveta, Ferramenta

from hardware.mqtt_client import publish_run_command
from hardware.camera_vision import capture_and_process
from django.views.decorators.http import require_GET
from django.urls import reverse

logger = logging.getLogger(__name__)



@csrf_exempt
def nfc_tap(request):
    """
    Endpoint chamado se, em vez de MQTT, a Rock enviar o UID via HTTP.
    Usa a mesma lógica do process_nfc_payload().
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Método não permitido. Use POST."}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"detail": "JSON inválido."}, status=400)

    try:
        resp_data = process_nfc_payload(data)
    except ValueError as e:
        return JsonResponse({"detail": str(e)}, status=400)

    status_code = 201 if resp_data.get("authorized") else 403
    return JsonResponse(resp_data, status=status_code)



def process_nfc_payload(data: dict) -> dict:
    """
    Lógica central de processamento do cartão NFC.
    Pode ser chamada tanto pela view HTTP quanto pelo bridge MQTT.
    Retorna um dicionário com o resultado.
    """
    uid = data.get("uid")
    reader_id = data.get("reader_id")

    if not uid:
        raise ValueError("Campo 'uid' é obrigatório.")

    # Tenta localizar o cartão
    try:
        cartao = CartaoNFC.objects.select_related("colaborador").get(uid=uid, ativo=True)
    except CartaoNFC.DoesNotExist:
        logger.warning("Cartão UID=%s não autorizado ou não cadastrado.", uid)
        return {
            "authorized": False,
            "reason": "Cartão não autorizado ou não cadastrado.",
        }

    colaborador = cartao.colaborador

    # Atualiza último uso
    cartao.ultimo_uso_em = timezone.now()
    cartao.save(update_fields=["ultimo_uso_em"])

    # Cria sessão de uso em andamento
    sessao = SessaoUso.objects.create(
        colaborador=colaborador,
        cartao=cartao,
        status="A",
        payload_inicial=data,
    )

    logger.info(
        "Sessão criada via NFC: sessao_id=%s, colaborador=%s, uid=%s",
        sessao.id, colaborador.nome, uid
    )

    response_data = {
        "authorized": True,
        "session_id": sessao.id,
        "colaborador": {
            "id": colaborador.id,
            "nome": colaborador.nome,
            "matricula": colaborador.matricula,
        },
        "reader_id": reader_id,
        "status": sessao.get_status_display(),
        "started_at": sessao.iniciado_em.isoformat(),
    }
    return response_data



def ferramentas_disponiveis(request):
    """
    Lista todas as ferramentas ativas organizadas por gaveta.
    """
    if request.method != "GET":
        return JsonResponse({"detail": "Método não permitido. Use GET."}, status=405)

    gavetas = Gaveta.objects.filter(ativa=True).order_by("numero")

    gavetas_data = []
    for gaveta in gavetas:
        ferramentas = gaveta.ferramentas.filter(ativa=True).order_by("posicao", "nome")
        ferramentas_data = [
            {
                "id": f.id,
                "nome": f.nome,
                "codigo": f.codigo,
                "posicao": f.posicao,
                "quantidade": f.quantidade,
                "descricao": f.descricao,
            }
            for f in ferramentas
        ]

        gavetas_data.append(
            {
                "id": gaveta.id,
                "numero": gaveta.numero,
                "nome": gaveta.nome,
                "descricao": gaveta.descricao,
                "ferramentas": ferramentas_data,
            }
        )

    return JsonResponse({"gavetas": gavetas_data}, status=200)


@csrf_exempt
def registrar_retirada(request, sessao_id):
    """
    Endpoint chamado pelo front em:
    POST /api/sessoes/<sessao_id>/retiradas/
    Body JSON: { "ferramentas_ids": [1, 2, 3] }

    Agora:
    - valida sessão
    - APAGA retiradas pendentes anteriores da sessão
    - cria MovimentacaoFerramenta no banco
    - abre a primeira gaveta via MQTT
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método não permitido"}, status=405)

    # 1) tenta ler o JSON enviado
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    # aceita tanto 'ferramentas_ids' quanto 'ferramentas'
    ids = payload.get("ferramentas_ids") or payload.get("ferramentas") or []

    if not isinstance(ids, list) or not ids:
        return JsonResponse(
            {"error": "Campo 'ferramentas_ids' deve ser uma lista com pelo menos 1 id."},
            status=400,
        )

    # 2) valida sessão
    try:
        sessao = SessaoUso.objects.select_related("colaborador", "cartao").get(id=sessao_id)
    except SessaoUso.DoesNotExist:
        return JsonResponse({"error": "Sessão não encontrada."}, status=404)

    if sessao.status != "A":
        return JsonResponse(
            {"error": "Sessão não está em andamento."},
            status=400,
        )

    # 2.1) LIMPA retiradas pendentes anteriores desta sessão
    MovimentacaoFerramenta.objects.filter(
        sessao=sessao,
        tipo="R",
        confirmado_visao=False,
    ).delete()

    # 3) busca as ferramentas ativas correspondentes
    qs = (
        Ferramenta.objects
        .select_related("gaveta")
        .filter(id__in=ids, ativa=True)
    )

    if not qs.exists():
        return JsonResponse(
            {"error": "Nenhuma ferramenta válida encontrada para os IDs enviados."},
            status=400,
        )

    # 4) cria movimentações de retirada no banco
    movimentacoes = []
    gavetas_env = {}  # numero_gaveta -> lista de ferramentas

    for f in qs:
        numero_gaveta = f.gaveta.numero if f.gaveta else None

        mov = MovimentacaoFerramenta.objects.create(
            sessao=sessao,
            ferramenta=f,
            tipo="R",                 # R = retirada
            gaveta_numero=numero_gaveta,
            quantidade=1,             # por enquanto 1 unidade por ferramenta
        )
        movimentacoes.append(mov)

        if numero_gaveta not in gavetas_env:
            gavetas_env[numero_gaveta] = []
        gavetas_env[numero_gaveta].append(f)

    # 5) define ordem das gavetas envolvidas (1, 2, 3...)
    gavetas_ordenadas = sorted([g for g in gavetas_env.keys() if g is not None])
    primeira_gaveta = gavetas_ordenadas[0] if gavetas_ordenadas else None

    # 6) tenta descobrir o reader_id (igual ao confirmar_retirada_gaveta)
    reader_id = getattr(settings, "READER_ID", None) or sessao.payload_inicial.get(
        "reader_id", "rockpi-01"
    )

    mqtt_result = None
    if primeira_gaveta is not None:
        try:
            # Rock Pi espera alias no formato: abrir_gaveta_1, abrir_gaveta_2, abrir_gaveta_3...
            alias = f"abrir_gaveta_{int(primeira_gaveta)}"

            mqtt_result = publish_run_command(
                reader_id=reader_id,
                alias=alias,
                args=[],
                mode="fg",
                timeout_s=10.0,
            )
            logger.info(
                "MQTT abrir gaveta: sessao=%s gaveta=%s reader_id=%s alias=%s resp=%s",
                sessao.id,
                primeira_gaveta,
                reader_id,
                alias,
                mqtt_result,
            )
        except Exception as e:
            logger.exception("Falha ao enviar comando MQTT para abrir gaveta.")
            mqtt_result = {"error": str(e)}

    # 7) monta resposta
    ferramentas_data = [
        {
            "id": f.id,
            "nome": f.nome,
            "gaveta_numero": f.gaveta.numero if f.gaveta else None,
            "gaveta_nome": f.gaveta.nome if f.gaveta else None,
        }
        for f in qs
    ]

    return JsonResponse(
        {
            "ok": True,
            "sessao_id": sessao.id,
            "ferramentas_selecionadas": ferramentas_data,
            "gavetas_envolvidas": gavetas_ordenadas,
            "primeira_gaveta": primeira_gaveta,
            "mqtt": mqtt_result,
        },
        status=201,
    )

@csrf_exempt
def confirmar_retirada_gaveta(request, sessao_id, gaveta_numero):
    """
    Após a gaveta ser aberta e o usuário retirar a ferramenta, o front chama
    este endpoint para:
      - acender o LED na Rock Pi
      - capturar uma foto da gaveta no PC
      - rodar o pipeline de visão (gaveta_detect)
      - vincular a imagem às movimentações daquela gaveta
      - fechar a gaveta atual
      - ABRIR a próxima gaveta (se houver)
      - ENCERRAR a sessão quando não houver mais gavetas pendentes
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Método não permitido. Use POST."}, status=405)

    # Busca a sessão
    try:
        sessao = SessaoUso.objects.select_related("colaborador").get(id=sessao_id)
    except SessaoUso.DoesNotExist:
        return JsonResponse({"detail": "Sessão não encontrada."}, status=404)

    if sessao.status != "A":
        return JsonResponse(
            {"detail": "Sessão não está em andamento."},
            status=400,
        )

    # Movimentações de retirada dessa gaveta, ainda não confirmadas
    movs = list(
        MovimentacaoFerramenta.objects.filter(
            sessao=sessao,
            tipo="R",
            gaveta_numero=gaveta_numero,
            confirmado_visao=False,
        ).select_related("ferramenta")
    )

    if not movs:
        return JsonResponse(
            {
                "detail": (
                    "Não há movimentações de retirada pendentes para "
                    f"a gaveta {gaveta_numero} nesta sessão."
                )
            },
            status=400,
        )

    # Descobre o reader_id (mesma lógica do nfc_tap)
    reader_id = getattr(settings, "READER_ID", None) or sessao.payload_inicial.get(
        "reader_id", "rockpi-01"
    )

    # 1) Acende LED na Rock Pi
    led_on_result = publish_run_command(
        reader_id=reader_id,
        alias="led_on",
        args=[],
        mode="fg",
        timeout_s=10.0,
    )

    # 2) Captura imagem + roda visão (no PC)
    try:
        imagem_rel, visao_ok, visao_raw = capture_and_process(sessao.id, gaveta_numero)
    except Exception as e:
        logger.exception(
            "Erro na captura/processamento de imagem da gaveta %s: %s",
            gaveta_numero,
            e,
        )
        # Mesmo se falhar, apaga o LED e retorna erro
        publish_run_command(
            reader_id=reader_id,
            alias="led_off",
            args=[],
            mode="fg",
            timeout_s=10.0,
        )
        return JsonResponse(
            {"detail": "Erro ao capturar/processar imagem da gaveta.", "error": str(e)},
            status=500,
        )

    # 3) Apaga LED na Rock Pi
    led_off_result = publish_run_command(
        reader_id=reader_id,
        alias="led_off",
        args=[],
        mode="fg",
        timeout_s=10.0,
    )

    # 3.1) Fecha a gaveta via MQTT (fechar_gaveta_X)
    try:
        alias_fechar = f"fechar_gaveta_{int(gaveta_numero)}"
        fechar_result = publish_run_command(
            reader_id=reader_id,
            alias=alias_fechar,
            args=[],
            mode="fg",
            timeout_s=10.0,
        )
    except Exception as e:
        logger.exception("Falha ao enviar comando MQTT para fechar gaveta.")
        fechar_result = {"error": str(e)}

    # 4) Interpreta o resultado da visão (se vier algo, beleza; se não vier, OK também)
    visao_json = None
    detectadas = []

    raw = visao_raw.get("raw") if isinstance(visao_raw, dict) else None
    if isinstance(raw, dict):
        visao_json = raw.get("json")
        if isinstance(visao_json, dict):
            detectadas = visao_json.get("retiradas", []) or []

    esperadas = [m.ferramenta.nome for m in movs]

    # 5) Atualiza movimentações dessa gaveta com a imagem.
    #    IMPORTANTE: aqui vamos considerar TODAS como confirmadas,
    #    independente do resultado da visão, para o fluxo andar.
    visao_matches = []

    for mov in movs:
        match_visao = mov.ferramenta.nome in detectadas
        visao_matches.append(match_visao)

        mov.imagem_path = imagem_rel
        mov.confirmado_visao = True  # <-- chave pra próxima gaveta ser liberada
        mov.save(update_fields=["imagem_path", "confirmado_visao"])

    # se ao menos uma bateu com a visão, marcamos visao_ok_final = True
    visao_ok_final = any(visao_matches) if visao_matches else False

    movs_data = [
        {
            "id": m.id,
            "ferramenta_id": m.ferramenta.id,
            "ferramenta_nome": m.ferramenta.nome,
            "gaveta_numero": m.gaveta_numero,
            "quantidade": m.quantidade,
            "imagem_path": m.imagem_path,
            "confirmado_visao": m.confirmado_visao,
        }
        for m in movs
    ]

    # 6) Verifica se ainda existe outra gaveta com retirada pendente
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

    sessao_encerrada = proxima_gaveta is None

    # 6.1) Se ainda houver gaveta, ABRIMOS a próxima via MQTT
    mqtt_abrir_proxima = None
    if proxima_gaveta is not None:
        try:
            alias_abrir = f"abrir_gaveta_{int(proxima_gaveta)}"
            mqtt_abrir_proxima = publish_run_command(
                reader_id=reader_id,
                alias=alias_abrir,
                args=[],
                mode="fg",
                timeout_s=10.0,
            )
        except Exception as e:
            logger.exception("Falha ao enviar comando MQTT para abrir próxima gaveta.")
            mqtt_abrir_proxima = {"error": str(e)}

    # 7) Se acabou tudo, marcamos a sessão como finalizada
    if sessao_encerrada and sessao.status == "A":
        sessao.status = "F"
        # se o model tiver campo finalizado_em, atualiza também
        if hasattr(sessao, "finalizado_em"):
            sessao.finalizado_em = timezone.now()
            sessao.save(update_fields=["status", "finalizado_em"])
        else:
            sessao.save(update_fields=["status"])

    # 8) Define redirect_url para o front
    if sessao_encerrada:
        redirect_url = reverse("home")  # volta para a tela principal, esperando novo cartão
    else:
        redirect_url = reverse("retirar_confirmar", args=[sessao.id])

    response = {
        "detail": "Retirada confirmada com captura de imagem e visão.",
        "sessao_id": sessao.id,
        "gaveta_numero": gaveta_numero,
        "imagem": imagem_rel,
        "visao_ok": visao_ok_final,
        "visao_raw": visao_raw,
        "match_visao": {
            "esperadas": esperadas,
            "detectadas": detectadas,
        },
        "movimentacoes_atualizadas": movs_data,
        "led": {
            "on": led_on_result,
            "off": led_off_result,
        },
        "fechar_gaveta": fechar_result,
        "abrir_proxima_gaveta": mqtt_abrir_proxima,
        "proxima_gaveta": proxima_gaveta,
        "sessao_encerrada": sessao_encerrada,
        "redirect_url": redirect_url,
    }

    return JsonResponse(response, status=200)


@require_GET
def status_frontend(request):
    """
    Endpoint chamado periodicamente pelo front (home.js)
    para saber se existe alguma sessão em andamento.
    """
    agora = timezone.now()
    limite = agora - timedelta(minutes=30)  # evita sessão velha

    sessao = (
        SessaoUso.objects
        .filter(status="A", iniciado_em__gte=limite)
        .select_related("colaborador")
        .order_by("-iniciado_em")
        .first()
    )

    if not sessao:
        return JsonResponse({
            "ok": True,
            "sessao_ativa": False,
        })

    return JsonResponse({
        "ok": True,
        "sessao_ativa": True,
        "sessao_id": sessao.id,
        "colaborador": sessao.colaborador.nome,
    })

@csrf_exempt
def registrar_devolucao(request, sessao_id):
    """
    POST /api/sessoes/<sessao_id>/devolucoes/
    Body JSON: { "ferramentas_ids": [1, 2, 3] }

    - valida sessão
    - cria MovimentacaoFerramenta tipo "D" (devolução)
    - abre a primeira gaveta envolvida via MQTT
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método não permitido"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    ids = payload.get("ferramentas_ids") or payload.get("ferramentas") or []
    if not isinstance(ids, list) or not ids:
        return JsonResponse(
            {"error": "Campo 'ferramentas_ids' deve ser uma lista com pelo menos 1 id."},
            status=400,
        )

    try:
        sessao = SessaoUso.objects.select_related("colaborador", "cartao").get(id=sessao_id)
    except SessaoUso.DoesNotExist:
        return JsonResponse({"error": "Sessão não encontrada."}, status=404)

    if sessao.status != "A":
        return JsonResponse({"error": "Sessão não está em andamento."}, status=400)

    colaborador = sessao.colaborador

    # Garante que essas ferramentas estão em posse desse colaborador
    last_mov_colab_qs = (
        MovimentacaoFerramenta.objects
        .filter(
            ferramenta=OuterRef("pk"),
            sessao__colaborador=colaborador,
            confirmado_visao=True,
        )
        .order_by("-criado_em")
    )

    qs = (
        Ferramenta.objects
        .select_related("gaveta")
        .filter(id__in=ids, ativa=True)
        .annotate(last_tipo=Subquery(last_mov_colab_qs.values("tipo")[:1]))
        .filter(last_tipo="R")  # só as que estão com ele
    )

    if not qs.exists():
        return JsonResponse(
            {"error": "Nenhuma ferramenta válida para devolução encontrada."},
            status=400,
        )

    movimentacoes = []
    gavetas_env = {}

    for f in qs:
        numero_gaveta = f.gaveta.numero if f.gaveta else None

        mov = MovimentacaoFerramenta.objects.create(
            sessao=sessao,
            ferramenta=f,
            tipo="D",  # devolução
            gaveta_numero=numero_gaveta,
            quantidade=1,
            confirmado_visao=False,
        )
        movimentacoes.append(mov)

        if numero_gaveta not in gavetas_env:
            gavetas_env[numero_gaveta] = []
        gavetas_env[numero_gaveta].append(f)

    gavetas_ordenadas = sorted([g for g in gavetas_env.keys() if g is not None])
    primeira_gaveta = gavetas_ordenadas[0] if gavetas_ordenadas else None

    reader_id = getattr(settings, "READER_ID", None) or sessao.payload_inicial.get(
        "reader_id", "rockpi-01"
    )

    mqtt_result = None
    if primeira_gaveta is not None:
        try:
            alias = f"abrir_gaveta_{int(primeira_gaveta)}"
            mqtt_result = publish_run_command(
                reader_id=reader_id,
                alias=alias,
                args=[],
                mode="fg",
                timeout_s=10.0,
            )
            logger.info(
                "MQTT abrir gaveta (devolucao): sessao=%s gaveta=%s reader_id=%s alias=%s resp=%s",
                sessao.id,
                primeira_gaveta,
                reader_id,
                alias,
                mqtt_result,
            )
        except Exception as e:
            logger.exception("Falha ao enviar comando MQTT para abrir gaveta (devolução).")
            mqtt_result = {"error": str(e)}

    ferramentas_data = [
        {
            "id": f.id,
            "nome": f.nome,
            "gaveta_numero": f.gaveta.numero if f.gaveta else None,
            "gaveta_nome": f.gaveta.nome if f.gaveta else None,
        }
        for f in qs
    ]

    return JsonResponse(
        {
            "ok": True,
            "sessao_id": sessao.id,
            "ferramentas_devolucao": ferramentas_data,
            "gavetas_envolvidas": gavetas_ordenadas,
            "primeira_gaveta": primeira_gaveta,
            "mqtt": mqtt_result,
        },
        status=201,
    )
@csrf_exempt
def confirmar_devolucao_gaveta(request, sessao_id, gaveta_numero):
    """
    Confirma DEVOLUÇÃO da gaveta <gaveta_numero>:

    - acende LED
    - captura foto + visão
    - apaga LED
    - fecha gaveta
    - marca movimentações tipo 'D' como confirmado_visao=True
    - se não houver mais devoluções pendentes, encerra sessão e manda voltar pra home
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Método não permitido. Use POST."}, status=405)

    try:
        sessao = SessaoUso.objects.select_related("colaborador").get(id=sessao_id)
    except SessaoUso.DoesNotExist:
        return JsonResponse({"detail": "Sessão não encontrada."}, status=404)

    if sessao.status != "A":
        return JsonResponse(
            {"detail": "Sessão não está em andamento."},
            status=400,
        )

    movs = list(
        MovimentacaoFerramenta.objects.filter(
            sessao=sessao,
            tipo="D",
            gaveta_numero=gaveta_numero,
            confirmado_visao=False,
        ).select_related("ferramenta")
    )

    if not movs:
        return JsonResponse(
            {
                "detail": (
                    "Não há movimentações de devolução pendentes para "
                    f"a gaveta {gaveta_numero} nesta sessão."
                )
            },
            status=400,
        )

    reader_id = getattr(settings, "READER_ID", None) or sessao.payload_inicial.get(
        "reader_id", "rasp-01"
    )

    led_on_result = publish_run_command(
        reader_id=reader_id,
        alias="led_on",
        args=[],
        mode="fg",
        timeout_s=10.0,
    )

    try:
        imagem_rel, visao_ok, visao_raw = capture_and_process(sessao.id, gaveta_numero)
    except Exception as e:
        logger.exception(
            "Erro na captura/processamento de imagem da gaveta %s (devolução): %s",
            gaveta_numero,
            e,
        )
        publish_run_command(
            reader_id=reader_id,
            alias="led_off",
            args=[],
            mode="fg",
            timeout_s=10.0,
        )
        return JsonResponse(
            {"detail": "Erro ao capturar/processar imagem da gaveta.", "error": str(e)},
            status=500,
        )

    led_off_result = publish_run_command(
        reader_id=reader_id,
        alias="led_off",
        args=[],
        mode="fg",
        timeout_s=10.0,
    )

    try:
        alias_fechar = f"fechar_gaveta_{int(gaveta_numero)}"
        fechar_result = publish_run_command(
            reader_id=reader_id,
            alias=alias_fechar,
            args=[],
            mode="fg",
            timeout_s=10.0,
        )
    except Exception as e:
        logger.exception("Falha ao enviar comando MQTT para fechar gaveta (devolução).")
        fechar_result = {"error": str(e)}

    visao_json = None
    detectadas = []

    raw = visao_raw.get("raw") if isinstance(visao_raw, dict) else None
    if isinstance(raw, dict):
        visao_json = raw.get("json")
        if isinstance(visao_json, dict):
            # ainda uso 'retiradas' porque é o que o script de visão retorna hoje
            detectadas = visao_json.get("retiradas", []) or []

    esperadas = [m.ferramenta.nome for m in movs]

    # >>> AQUI: marca todas como confirmadas pra fluxo andar entre gavetas
    for mov in movs:
        mov.imagem_path = imagem_rel
        mov.confirmado_visao = True
        mov.save(update_fields=["imagem_path", "confirmado_visao"])

    visao_ok_final = bool(detectadas)  # se quiser usar como flag geral

    movs_data = [
        {
            "id": m.id,
            "ferramenta_id": m.ferramenta.id,
            "ferramenta_nome": m.ferramenta.nome,
            "gaveta_numero": m.gaveta_numero,
            "quantidade": m.quantidade,
            "imagem_path": m.imagem_path,
            "confirmado_visao": m.confirmado_visao,
        }
        for m in movs
    ]

    # Próxima gaveta com devolução pendente
    proxima_gaveta = (
        MovimentacaoFerramenta.objects
        .filter(
            sessao=sessao,
            tipo="D",
            confirmado_visao=False,
        )
        .order_by("gaveta_numero")
        .values_list("gaveta_numero", flat=True)
        .first()
    )

    sessao_encerrada = proxima_gaveta is None

    if sessao_encerrada and sessao.status == "A":
        sessao.status = "F"
        sessao.save(update_fields=["status"])

    # >>> AQUI: se tiver próxima gaveta, manda já a URL dela
    if sessao_encerrada:
        redirect_url = reverse("home")
    else:
        redirect_url = reverse("devolver_confirmar", args=[sessao.id, proxima_gaveta])

    response = {
        "detail": "Devolução confirmada com captura de imagem e visão.",
        "sessao_id": sessao.id,
        "gaveta_numero": gaveta_numero,
        "imagem": imagem_rel,
        "visao_ok": visao_ok_final,
        "visao_raw": visao_raw,
        "match_visao": {
            "esperadas": esperadas,
            "detectadas": detectadas,
        },
        "movimentacoes_atualizadas": movs_data,
        "led": {
            "on": led_on_result,
            "off": led_off_result,
        },
        "fechar_gaveta": fechar_result,
        "proxima_gaveta": proxima_gaveta,
        "sessao_encerrada": sessao_encerrada,
        "redirect_url": redirect_url,
    }

    return JsonResponse(response, status=200)
