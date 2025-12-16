# 1_roi_picker.py
import json, os
import cv2 as cv

HELP = """
[ROI Picker - Nomeie suas ferramentas]
--------------------------------------
- Clique e arraste para desenhar um retângulo (ROI).
- Ao soltar o mouse, DIGITE no terminal o NOME da ferramenta e pressione Enter.
- Teclas:
   [z] → desfaz última ROI
   [s] → salva ROIs da gaveta atual
   [n] → próxima gaveta
   [q] → sair sem salvar
"""

GAVETAS = [
    {"nome": "Gaveta 1", "ref_path": "ref_vazia_gaveta1.jpg", "out_json": "rois_gaveta1.json"},
    {"nome": "Gaveta 2", "ref_path": "ref_vazia_gaveta2.jpg", "out_json": "rois_gaveta2.json"},
    {"nome": "Gaveta 3", "ref_path": "ref_vazia_gaveta3.jpg", "out_json": "rois_gaveta3.json"},
]

def gerar_rois_para(ref_path, out_json, nome_gaveta):
    if not os.path.exists(ref_path):
        raise SystemExit(f"[ERRO] Não achei {ref_path}. Coloque a foto de referência da {nome_gaveta}.")

    print(f"\n--- {nome_gaveta} ---")
    print(HELP)

    img = cv.imread(ref_path)
    clone = img.copy()
    rois = []  # lista de {"nome": str, "coords": [x,y,w,h]}

    drawing = False
    ix = iy = 0
    rect = None

    def redraw():
        img[:] = clone[:] = cv.imread(ref_path)
        for i, item in enumerate(rois, 1):
            x, y, w, h = item["coords"]
            cv.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv.putText(img, f"{i}: {item['nome']}", (x, y - 8),
                       cv.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    def mouse(event, x, y, flags, param):
        nonlocal drawing, ix, iy, rect, img
        if event == cv.EVENT_LBUTTONDOWN:
            drawing = True
            ix, iy = x, y
            rect = None
        elif event == cv.EVENT_MOUSEMOVE and drawing:
            img[:] = clone
            cv.rectangle(img, (ix, iy), (x, y), (0, 255, 0), 2)
        elif event == cv.EVENT_LBUTTONUP:
            drawing = False
            x0, y0 = min(ix, x), min(iy, y)
            x1, y1 = max(ix, x), max(iy, y)
            w, h = x1 - x0, y1 - y0
            rect = (x0, y0, w, h)
            redraw()
            cv.rectangle(img, (x0, y0), (x1, y1), (0, 255, 0), 2)
            cv.imshow("ROI Picker", img)

            # pede nome no terminal
            nome = input("Digite o NOME da ferramenta para esta ROI (ou deixe vazio para descartar): ").strip()
            if nome:
                rois.append({"nome": nome, "coords": [int(x0), int(y0), int(w), int(h)]})
                print(f"[OK] ROI adicionada → {nome} @ {x0,y0,w,h}")
                redraw()
            else:
                print("[INFO] ROI descartada.")
                redraw()

    cv.namedWindow("ROI Picker", cv.WINDOW_NORMAL)
    cv.setMouseCallback("ROI Picker", mouse)

    while True:
        cv.imshow("ROI Picker", img)
        k = cv.waitKey(20) & 0xFF
        if k == ord('z'):
            if rois:
                removed = rois.pop()
                print(f"[UNDO] Removido: {removed['nome']}")
                redraw()
        elif k == ord('s'):
            if not rois:
                print("Nenhuma ROI definida.")
                continue
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(rois, f, ensure_ascii=False, indent=2)
            print(f"[OK] Salvo {out_json} ({len(rois)} itens).")
            break
        elif k == ord('n'):
            print("[INFO] Próxima gaveta...")
            return
        elif k == ord('q'):
            print("[INFO] Saindo sem salvar.")
            cv.destroyAllWindows()
            raise SystemExit(0)

    cv.destroyAllWindows()

def main():
    for gaveta in GAVETAS:
        gerar_rois_para(gaveta["ref_path"], gaveta["out_json"], gaveta["nome"])
        print(f"\n[✔] ROIs da {gaveta['nome']} concluídas. Enter para continuar...")
        input()
    print("\n=== Tudo pronto! ===")
    print("Exemplo:")
    print("  python gaveta_detect.py --image teste1.jpg --ref ref_vazia_gaveta1.jpg --rois rois_gaveta1.json --save saida1.jpg")

if __name__ == "__main__":
    main()
