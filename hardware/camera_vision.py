import os
import json
import logging
import subprocess
import sys

import cv2 as cv
from django.conf import settings

logger = logging.getLogger(__name__)
# Config da câmera 
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
CAMERA_WARMUP_FRAMES = int(os.getenv("CAMERA_WARMUP_FRAMES", "10"))

# Resolução alvo FULL HD
TARGET_W = int(os.getenv("VISION_TARGET_WIDTH", "1920"))
TARGET_H = int(os.getenv("VISION_TARGET_HEIGHT", "1080"))


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def capture_and_process(sessao_id: int, gaveta_numero: int):
    """
    Captura uma imagem da câmera, força para TARGET_W x TARGET_H,
    salva em media/sessoes/<sessao_id>/, roda gaveta_detect.py
    e também força a imagem de saída para a mesma resolução.
    Retorna (caminho_relativo_da_imagem_sessao, visao_ok, debug_dict).
    """

    media_root = settings.MEDIA_ROOT
    sessao_dir = os.path.join(media_root, "sessoes", str(sessao_id))
    os.makedirs(sessao_dir, exist_ok=True)

    # ---------- NOME DA IMAGEM BRUTA DA SESSÃO ----------
    image_name = f"sessao{sessao_id}_gaveta{gaveta_numero}.jpg"
    image_abs = os.path.join(sessao_dir, image_name)

    # ---------- ABRE A CÂMERA ----------
    cap = cv.VideoCapture(CAMERA_INDEX, cv.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        raise RuntimeError("Não foi possível abrir a câmera")

    # tenta forçar codec MJPG (muitas câmeras liberam resoluções maiores com esse codec)
    try:
        fourcc = cv.VideoWriter_fourcc(*"MJPG")
        cap.set(cv.CAP_PROP_FOURCC, fourcc)
    except Exception:
        pass

    # tenta forçar resolução grande direto na câmera
    cap.set(cv.CAP_PROP_FRAME_WIDTH, TARGET_W)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, TARGET_H)

    # warmup: lê alguns frames para estabilizar exposição/foco
    for _ in range(CAMERA_WARMUP_FRAMES):
        cap.read()

    ok, frame = cap.read()
    cap.release()

    if not ok or frame is None:
        raise RuntimeError("Falha ao capturar frame da câmera")

    # resolução original que a câmera entregou
    h0, w0 = frame.shape[:2]

    # ---------- FORÇA RESIZE PARA TARGET_W x TARGET_H ANTES DE SALVAR ----------
    frame_resized = cv.resize(frame, (TARGET_W, TARGET_H), interpolation=cv.INTER_CUBIC)
    cv.imwrite(image_abs, frame_resized)

    # Confere o que realmente foi salvo em disco
    check = cv.imread(image_abs)
    if check is not None:
        hc, wc = check.shape[:2]
    else:
        hc, wc = None, None

    # ---------- RODA O SCRIPT DE VISÃO ----------
    gaveta_detect_path = os.path.join(settings.BASE_DIR, "visao", "gaveta_detect.py")
    ref_path = os.path.join(settings.BASE_DIR, "visao", f"ref_vazia_gaveta{gaveta_numero}.jpg")
    rois_path = os.path.join(settings.BASE_DIR, "visao", f"rois_gaveta{gaveta_numero}.json")

    saida_name = f"sessao{sessao_id}_gaveta{gaveta_numero}_saida.jpg"
    saida_abs = os.path.join(sessao_dir, saida_name)

    cmd = [
        sys.executable,
        gaveta_detect_path,
        "--image", image_abs,
        "--ref", ref_path,
        "--rois", rois_path,
        "--save", saida_abs,
    ]

    p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    stdout = p.stdout or ""
    stderr = p.stderr or ""
    visao_ok = (p.returncode == 0)

    # ---------- GARANTE QUE A IMAGEM DE SAÍDA TAMBÉM SEJA TARGET_W x TARGET_H ----------
    saida_before_w = None
    saida_before_h = None
    saida_after_w = None
    saida_after_h = None

    if os.path.exists(saida_abs):
        out_img = cv.imread(saida_abs)
        if out_img is not None:
            oh, ow = out_img.shape[:2]
            saida_before_w, saida_before_h = ow, oh

            if (ow, oh) != (TARGET_W, TARGET_H):
                out_resized = cv.resize(out_img, (TARGET_W, TARGET_H), interpolation=cv.INTER_CUBIC)
                cv.imwrite(saida_abs, out_resized)
                saida_after_w, saida_after_h = TARGET_W, TARGET_H
            else:
                saida_after_w, saida_after_h = ow, oh

    # ---------- TENTA LER O JSON DISPONIBILIZADO PELO GAVETA_DETECT ----------
    json_out = None
    try:
        last_line = stdout.strip().splitlines()[-1]
        json_out = json.loads(last_line)
    except Exception:
        json_out = None

    image_rel = os.path.join("sessoes", str(sessao_id), image_name)

    # ---------- META DE DEBUG: RESOLUÇÕES ----------
    meta = {
        "camera_original": {"width": w0, "height": h0},
        "sessao_salva": {"width": wc, "height": hc},
        "saida_before": {"width": saida_before_w, "height": saida_before_h},
        "saida_after": {"width": saida_after_w, "height": saida_after_h},
        "target": {"width": TARGET_W, "height": TARGET_H},
    }

    return image_rel, visao_ok, {
        "ok": visao_ok,
        "raw": {
            "stdout": stdout[-1000:],
            "stderr": stderr[-1000:],
            "json": json_out,
            "meta": meta,
        },
    }

def run_gaveta_detect(image_path: str, gaveta_numero: int) -> dict:
    """
    Chama o gaveta_detect.py dentro do app 'visao', usando:
      --ref   ref_vazia_gavetaX.jpg
      --rois  rois_gavetaX.json
      --image <imagem capturada>
      --save  <imagem anotada>

    O gaveta_detect.py vai gerar:
      - imagem anotada *_saida.jpg
      - JSON *_saida.json com o resultado
    """

    # Caminho do gaveta_detect.py dentro do projeto Django
    script_path = os.path.join(
        settings.BASE_DIR,
        "visao",
        "gaveta_detect.py",
    )

    # Arquivos de referência e ROIs por gaveta
    ref_path = os.path.join(
        settings.BASE_DIR,
        "visao",
        f"ref_vazia_gaveta{gaveta_numero}.jpg",
    )
    rois_path = os.path.join(
        settings.BASE_DIR,
        "visao",
        f"rois_gaveta{gaveta_numero}.json",
    )

    logger.info("Usando gaveta_detect.py em: %s", script_path)
    logger.info("Ref: %s | ROIs: %s", ref_path, rois_path)

    # Verificações básicas
    if not os.path.exists(script_path):
        logger.error("gaveta_detect.py não encontrado em %s", script_path)
        return {
            "ok": False,
            "raw": {
                "error": "gaveta_detect.py não encontrado",
                "path": script_path,
            },
        }

    if not os.path.exists(ref_path) or not os.path.exists(rois_path):
        logger.error("Arquivos de ref/rois não encontrados: %s / %s", ref_path, rois_path)
        return {
            "ok": False,
            "raw": {
                "error": "Arquivos de ref/rois não encontrados",
                "ref": ref_path,
                "rois": rois_path,
            },
        }

    # Ex.: .../sessao4_gaveta3_2025...jpg -> ..._saida.jpg / ..._saida.json
    base, _ = os.path.splitext(image_path)
    save_path = base + "_saida.jpg"
    json_path = base + "_saida.json"

    cmd = [
        sys.executable,
        script_path,
        "--ref",
        ref_path,
        "--rois",
        rois_path,
        "--image",
        image_path,
        "--gaveta-id",
        str(gaveta_numero),
        "--save",
        save_path,
    ]

    logger.info("Executando visão: %s", cmd)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        logger.error("Timeout ao executar gaveta_detect.py")
        return {"ok": False, "raw": {"error": "timeout"}}

    stdout = (proc.stdout or "")[-800:]
    stderr = (proc.stderr or "")[-800:]

    logger.info("gaveta_detect stdout: %s", stdout)
    if stderr:
        logger.warning("gaveta_detect stderr: %s", stderr)

    ok_proc = proc.returncode == 0

    # Tenta ler o JSON gerado
    result_json = None
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                result_json = json.load(f)
        except Exception as e:
            logger.error("Erro ao ler JSON de visão %s: %s", json_path, e)

    ok_final = ok_proc
    if isinstance(result_json, dict) and "ok" in result_json:
        if isinstance(result_json["ok"], bool):
            ok_final = result_json["ok"]

    return {
        "ok": ok_final,
        "raw": {
            "stdout": stdout,
            "stderr": stderr,
            "json": result_json,
        },
    }



