# gaveta_detect.py (apenas cole por cima do seu arquivo atual)
import argparse, json, os, sys, traceback, time
import numpy as np
import cv2 as cv
from skimage.metrics import structural_similarity as ssim

try:
    import requests
except ImportError:
    requests = None  # só será usado se --post for passado

EDGE_DELTA_EMPTY = 0.02
EDGE_DELTA_OCC   = 0.06
SSIM_EMPTY_OK    = 0.85
SSIM_OCC_BAD     = 0.20
DIFF_MEAN_OCC    = 0.18
HIST_CORR_EMPTY  = 0.990

def log(m): 
    print(f"[LOG] {m}", flush=True)

def clamp_roi(roi, W, H):
    x, y, w, h = roi
    x = max(0, min(x, W-1))
    y = max(0, min(y, H-1))
    w = max(1, min(w, W - x))
    h = max(1, min(h, H - y))
    return (x, y, w, h)

def preprocess_gray(bgr):
    g = cv.cvtColor(bgr, cv.COLOR_BGR2GRAY)
    g = cv.GaussianBlur(g, (5,5), 0)
    g = cv.equalizeHist(g)
    return g

def roi_metrics(ref_bgr, cur_bgr, roi):
    H, W = ref_bgr.shape[:2]
    x, y, w, h = clamp_roi(roi, W, H)
    r_ref = ref_bgr[y:y+h, x:x+w]
    r_cur = cur_bgr[y:y+h, x:x+w]

    ref_g = preprocess_gray(r_ref)
    cur_g = preprocess_gray(r_cur)

    m = min(ref_g.shape[0], ref_g.shape[1])
    win = max(3, min(7, m if m % 2 else m-1))
    s = ssim(ref_g, cur_g, win_size=win)

    ref_e = cv.Canny(ref_g, 60, 140)
    cur_e = cv.Canny(cur_g, 60, 140)
    ref_edge = (ref_e > 0).mean()
    cur_edge = (cur_e > 0).mean()
    delta_edge = max(0.0, cur_edge - ref_edge)

    diff_mean = float(np.mean(np.abs(cur_g.astype(np.int16) - ref_g.astype(np.int16))) / 255.0)

    ref_v = cv.cvtColor(r_ref, cv.COLOR_BGR2HSV)[:,:,2]
    cur_v = cv.cvtColor(r_cur, cv.COLOR_BGR2HSV)[:,:,2]
    ref_hist = cv.calcHist([ref_v],[0],None,[32],[0,256])
    cur_hist = cv.calcHist([cur_v],[0],None,[32],[0,256])
    ref_hist = cv.normalize(ref_hist, ref_hist).flatten()
    cur_hist = cv.normalize(cur_hist, cur_hist).flatten()
    hist_corr = float(cv.compareHist(ref_hist, cur_hist, cv.HISTCMP_CORREL))

    return dict(
        rect=(x,y,w,h),
        ssim=float(s),
        edge=float(cur_edge),
        ref_edge=float(ref_edge),
        delta_edge=float(delta_edge),
        diff_mean=diff_mean,
        hist_corr=hist_corr,
    )

def decide_presence(m):
    s, d, df, hc = m["ssim"], m["delta_edge"], m["diff_mean"], m["hist_corr"]
    if d <= EDGE_DELTA_EMPTY and hc >= HIST_CORR_EMPTY:
        return False
    if d >= EDGE_DELTA_OCC:
        return True
    if df >= DIFF_MEAN_OCC and s <= SSIM_OCC_BAD:
        return True
    if s >= SSIM_EMPTY_OK and d <= EDGE_DELTA_EMPTY:
        return False
    if hc >= (HIST_CORR_EMPTY - 0.01) and df < (DIFF_MEAN_OCC * 0.5):
        return False
    return df >= (DIFF_MEAN_OCC * 0.7) and s <= 0.5

def draw_result(img, name, m, present):
    x, y, w, h = m["rect"]
    color = (0,255,0) if present else (0,0,255)
    cv.rectangle(img, (x,y), (x+w,y+h), color, 2)
    label = (
        f"{name}: {'OCUPADO' if present else 'VAZIO'} | "
        f"s={m['ssim']:.2f} | e={m['edge']:.3f} | ref={m['ref_edge']:.3f} | "
        f"d={m['delta_edge']:.3f} | diff={m['diff_mean']:.3f} | hc={m['hist_corr']:.3f}"
    )
    cv.putText(img, label, (x, y-8), cv.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

def load_rois(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    rois = {}
    if isinstance(data, dict):
        for k, v in data.items():
            rois[k] = tuple(map(int, v))
    elif isinstance(data, list):
        for item in data:
            name = item.get("nome", f"roi_{len(rois)+1}")
            rois[name] = tuple(map(int, item["coords"]))
    else:
        raise ValueError("Formato de JSON inválido para ROIs.")
    return rois

def main():
    ap = argparse.ArgumentParser(description="Detecção de ferramentas por ROI fixa")
    ap.add_argument("--ref",   required=True, help="Imagem de referência vazia")
    ap.add_argument("--rois",  required=True, help="Arquivo JSON com as ROIs")
    ap.add_argument("--image", required=True, help="Imagem atual da gaveta")
    ap.add_argument("--save",  default="saida.jpg", help="Nome da imagem de saída anotada")

    # Metadados para BD
    ap.add_argument("--usuario",   help="ID ou matrícula do colaborador (RFID/NFC)")
    ap.add_argument("--gaveta-id", help="Identificador da gaveta (ex.: 1,2,3)")
    ap.add_argument("--esperada",  help="Nome da ferramenta escolhida no display (comparação)")

    # Envio para API
    ap.add_argument("--post", help="URL da API Flask para registrar o evento (POST JSON)")
    args = ap.parse_args()

    try:
        for p in [args.ref, args.rois, args.image]:
            log(f"Checando: {p} -> {'OK' if os.path.exists(p) else 'NÃO ENCONTRADO'}")

        ref = cv.imread(args.ref)
        cur = cv.imread(args.image)
        if ref is None or cur is None:
            raise RuntimeError("Erro ao carregar imagens.")

        rois = load_rois(args.rois)
        cur = cv.resize(cur, (ref.shape[1], ref.shape[0]))

        out = cur.copy()
        statuses = {}
        retiradas = []  # nomes presentes=True (ocupado) → ferramenta retirada
        for name, roi in rois.items():
            m = roi_metrics(ref, cur, roi)
            present = decide_presence(m)
            draw_result(out, name, m, present)
            statuses[name] = {"presente": bool(present), **m}
            if present:  # "presente" aqui significa OCUPADO NA IMAGEM ATUAL (ou seja, diferente do ref vazio)
                retiradas.append(name)

        cv.imwrite(args.save, out)
        log(f"Imagem salva em '{args.save}'")

        # Consolidado para BD/API
        ts = int(time.time())
        result = {
            "timestamp": ts,
            "usuario": args.usuario,
            "gaveta_id": args.gaveta_id,
            "imagem_saida": args.save,
            "ref": os.path.basename(args.ref),
            "rois": os.path.basename(args.rois),
            "detalhes": statuses,
            "retiradas": retiradas,          # lista com nomes das ferramentas detectadas como "ocupado"
            "esperada": args.esperada or "",
            "ok": (args.esperada in retiradas) if args.esperada else None
        }

        # Salva JSON local junto da saída
        json_out = os.path.splitext(args.save)[0] + ".json"
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        log(f"STATUS FINAL JSON: {json_out}")
        print(json.dumps(result, ensure_ascii=False))

        # POST opcional para API
        if args.post:
            if requests is None:
                raise RuntimeError("Para --post é preciso 'pip install requests'.")
            try:
                r = requests.post(args.post, json=result, timeout=5)
                log(f"POST {args.post} -> {r.status_code} {r.text[:120]}")
            except Exception as e:
                log(f"[WARN] Falha no POST: {e}")

    except Exception as e:
        print("[ERRO]", e)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
